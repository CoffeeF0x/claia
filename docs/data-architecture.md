# CLAIA Data Architecture

Reference for how CLAIA models, events, and storage work.

---

## Design Principles

1. **Models are pure Python objects.** No persistence logic, no file paths, no database dependencies. A `Conversation` can exist entirely in memory.
2. **Persistence is the host runtime's job.** The CLI saves JSON files. The Slate API will use a database. CLAIA's models don't care which.
3. **Domain events are the single mutation record.** Every state change emits a `DomainEvent` that both persists to the audit trail and notifies runtime listeners. There is no separate "action" system.
4. **Everything round-trips through `to_dict()` / `from_dict()`.** Serialization is always a plain dict. The host runtime decides the wire format (JSON files, database rows, API responses).
5. **Model IO contract: sequence or artifacts in, `ModelResponse` out.** Deployments translate conversations using `supported_inputs`. Chunks are content only; status lives on the response wrapper.

---

## Layout

```
claia/core/
  enums/data/          # MediaType + per-category format enums
  data/
    common/            # DataObject
    artifacts/         # durable IO payloads (in)
    chunks/            # streamed content pieces (out)
    response.py        # ModelResponse
    models/            # Conversation, Message, MessageSequence(Ordered), Prompt
                       #   Conversation.to_message_sequence() / deployment.translate()
```

---

## Inheritance

```
DataObject                 # type, format, name, metadata
├── BaseArtifact           # + guid, original
│   ├── TextArtifact
│   ├── ImageArtifact
│   ├── AudioArtifact
│   ├── FileArtifact
│   ├── LinkArtifact
│   ├── RawArtifact
│   └── ToolArtifact
└── BaseChunk
    ├── TextChunk
    ├── ImageChunk
    ├── AudioChunk
    └── RawChunk
```

`Conversation`, `Message`, and `Prompt` are conversation-domain types under `data/models/` — they do **not** inherit from artifacts.

---

## DataObject

Shared base for artifacts and chunks.

| Field | Type | Description |
|---|---|---|
| `type` | `MediaType` | IANA top-level media type |
| `format` | format enum | Per-category subtype (`TextFormat`, `ImageFormat`, …) |
| `name` | `str` | Human-readable label |
| `metadata` | `dict` | Freeform bag |

`media_type` is derived as `f"{type.value}/{format.value}"`.

MIME enums live in `claia.core.enums.data`:

- `MediaType` — IANA top-level (`text`, `image`, `audio`, `video`, `application`, …)
- `TextFormat`, `ImageFormat`, `AudioFormat`, `VideoFormat`, `ApplicationFormat`

---

## Artifacts (inputs / durable)

| Class | Typical `type` | Payload |
|---|---|---|
| `TextArtifact` | `TEXT` | `str` |
| `ImageArtifact` | `IMAGE` | bytes (+ optional PIL) |
| `AudioArtifact` | `AUDIO` | bytes |
| `FileArtifact` | `APPLICATION` | bytes (pdf, docx, …) |
| `LinkArtifact` | `TEXT` + `URI_LIST` | URI string |
| `RawArtifact` | `APPLICATION` + `OCTET_STREAM` | opaque bytes |

Artifact-only fields:

| Field | Type | Description |
|---|---|---|
| `guid` | `str` | Stable identity (`id` is an alias) |
| `original` | `str \| None` | Guid of the pre-conversion artifact |

```python
from claia.core.data import TextArtifact
from claia.core.enums.data import TextFormat

t = TextArtifact.from_content("hello", name="notes.txt", format=TextFormat.PLAIN)
d = t.to_dict()
t2 = TextArtifact.from_dict(d)
```

---

## Chunks (outputs / stream)

Content only — no progress/done/error chunks.

| Class | Payload |
|---|---|
| `TextChunk` | `str` |
| `ImageChunk` | `bytes` |
| `AudioChunk` | `bytes` |
| `RawChunk` | `bytes` |

No file/link chunks (not native model outputs).

---

## ModelResponse

Returned by `BaseModel.generate`. Carries content plus status:

| Field | Type | Description |
|---|---|---|
| `chunks` | `list[BaseChunk]` | Content produced |
| `complete` | `bool` | Finished successfully / fully |
| `error` | `Any \| None` | Optional error info |
| `metadata` | `dict` | Usage, finish_reason, … |

Streaming models may yield `BaseChunk` items and `return` a `ModelResponse` via the generator return value. Deployments translate a `Conversation` via `BaseDeployment.translate(conversation, definition)` into a `MessageSequence` / `MessageSequenceOrdered` or a latest-message artifact list before calling the model.

```python
from claia.core.data import ModelResponse, TextChunk

response = ModelResponse(chunks=[TextChunk(data="hi")], complete=True)
assert response.text() == "hi"
```

---

## Conversation

Conversation-domain object (not an artifact). Host runtimes persist it.

### Core Fields

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Conversation UUID |
| `title` | `str` | Display title |
| `prompt` | `dict` | `{"system": "..."}` — system prompt |
| `messages` | `List[Message]` | All message nodes (full tree, all branches) |
| `active_head_id` | `str \| None` | Leaf message ID of the active branch |
| `events` | `List[DomainEvent]` | Persisted audit trail of all mutations |

Generation parameters (temperature, max_tokens, streaming, ...) do not
live on `Conversation`. Architectures/models declare them as RUNTIME
`ParamSpec`s and callers supply them per-call via `Process.parameters`
or `Registry.run(..., **kwargs)`.

### Message Tree

Messages form a directed tree via `parent_id`. Multiple children of the same parent represent branches (edits/versions).

`active_head_id` points to the tip of the currently active branch. `get_thread(head_id?)` walks backwards from a leaf to the root and returns messages in chronological order.

### Message

| Field | Type | Description |
|---|---|---|
| `message_id` | `str` | UUID |
| `parent_id` | `str \| None` | Parent in the message tree |
| `speaker` | `MessageRole` | `USER`, `ASSISTANT`, `SYSTEM`, `INTERNAL`, … |
| `artifacts` | `List[BaseArtifact]` | Ordered payload (text, image, file, link, …) |
| `content` | `str` (accessor) | Primary text artifact convenience view |
| `inline_args` | `dict` | Extracted inline arguments from content |
| `created_at` | `float` | Unix timestamp |
| `updated_at` | `float` | Unix timestamp |

### Prompt

Standalone conversation-domain object (not a `TextArtifact`). Has `prompt_name` (validated lowercase-hyphen slug) and `prompt_type`.

---

## Domain Events

Every conversation mutation emits a `DomainEvent` recorded on the conversation and dispatched to an optional observer. Streaming appends do not fire per-chunk events — hosts flush on their own cadence.

---

## Persistence Boundary

- CLI: `JsonStore` writes JSON files under type-based subdirectories (`texts/`, `images/`, `audio/`, `files/`, `prompts/`, `conversations/`).
- Slate / other hosts: own database schemas; consume `to_dict()` / domain events.
- Core never opens files or databases for model data.

---

## Modality

`claia.core.modality.Modality` remains a **capability advertisement** on `ModelDefinition` (`input_modalities` / `output_modalities`). It is independent of the artifact/chunk payload types.
