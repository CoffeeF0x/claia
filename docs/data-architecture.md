# CLAIA Data Architecture

Reference for how CLAIA models, events, and storage work after the data layer overhaul. Written as a guide for building the Slate API integration and ai.exofox.dev frontend.

---

## Design Principles

1. **Models are pure Python objects.** No persistence logic, no file paths, no database dependencies. A `Conversation` can exist entirely in memory.
2. **Persistence is the host runtime's job.** The CLI saves JSON files. The Slate API will use a database. CLAIA's models don't care which.
3. **Domain events are the single mutation record.** Every state change emits a `DomainEvent` that both persists to the audit trail and notifies runtime listeners. There is no separate "action" system.
4. **Everything round-trips through `to_dict()` / `from_dict()`.** Serialization is always a plain dict. The host runtime decides the wire format (JSON files, database rows, API responses).

---

## Model Hierarchy

```
BaseArtifact (ABC)
├── TextArtifact
│   ├── Prompt
│   └── Conversation
├── ImageArtifact
└── AudioArtifact
```

All models live in `claia.lib.data.models` and are re-exported from `claia.lib.data`.

### BaseArtifact

The root of all artifact types. Provides identity, naming, timestamps, and content caching.

| Field | Type | Description |
|---|---|---|
| `id` | `str` | UUID, auto-generated if not provided |
| `name` | `str` | Human-readable name (e.g. `"chat-abc.json"`) |
| `media_type` | `str` | MIME type, auto-detected from name if omitted |
| `size` | `int` | Content size in bytes |
| `is_reference` | `bool` | Whether this points to an external source |
| `source_uri` | `str \| None` | Path or URL if `is_reference` is true |
| `metadata` | `dict` | Freeform metadata bag |
| `created_at` | `float` | Unix timestamp |
| `updated_at` | `float` | Unix timestamp |

Constructor: all fields are keyword arguments with sensible defaults.

```python
from claia.lib.data import TextArtifact

t = TextArtifact(name="notes.txt")
d = t.to_dict()   # plain dict, no legacy keys
t2 = TextArtifact.from_dict(d)
```

Key methods:
- `to_dict() -> dict` — serialize metadata (excludes binary content)
- `from_dict(data) -> Self` — class method, deserialize
- `load_content()` — abstract, subclass implements
- `set_content(data)` — store content in memory
- `has_content_loaded() -> bool`

### TextArtifact

Adds `encoding` (default `"utf-8"`). Content is a `str`.

Factory methods: `from_content(content, name)`, `from_path(source)`, `from_url(url)`

### Prompt

Extends `TextArtifact`. Adds `prompt_name` (validated lowercase-hyphen slug) and `prompt_type`.

### ImageArtifact

Adds `width`, `height`, `format`. Content is a PIL `Image` object.

Factory methods: `from_image(image_obj, name)`, `from_bytes(image_data, name)`, `from_path(source)`, `from_url(url)`

### AudioArtifact

Adds `duration`, `format`, `sample_rate`, `channels`. Content is `bytes`.

Factory methods: `from_bytes(audio_data, name)`, `from_path(source)`, `from_url(url)`

---

## Conversation

The most complex model. Extends `TextArtifact` (serializes as JSON text).

### Core Fields

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Conversation UUID |
| `title` | `str` | Display title |
| `prompt` | `dict` | `{"system": "..."}` — system prompt |
| `messages` | `List[Message]` | All message nodes (full tree, all branches) |
| `active_head_id` | `str \| None` | Leaf message ID of the active branch |
| `events` | `List[DomainEvent]` | Persisted audit trail of all mutations |
| `settings` | `ConversationSettings` | Generation parameters |

### Message Tree

Messages form a directed tree via `parent_id`. Multiple children of the same parent represent branches (edits/versions).

```
msg-1 (user: "hello")
└── msg-2 (assistant: "hi there")
    ├── msg-3 (user: "tell me a joke")     ← branch A
    │   └── msg-4 (assistant: "why did...")
    └── msg-5 (user: "what's the weather") ← branch B
```

`active_head_id` points to the tip of the currently active branch. `get_thread(head_id?)` walks backwards from a leaf to the root and returns messages in chronological order.

Key tree methods:
- `get_thread(head_id=None)` — active linear thread
- `get_siblings(message_id)` — all messages sharing the same parent
- `get_branch_head(message_id)` — find the deepest leaf reachable from a node

### Message

| Field | Type | Description |
|---|---|---|
| `message_id` | `str` | UUID |
| `parent_id` | `str \| None` | Parent in the message tree |
| `speaker` | `MessageRole` | `USER`, `ASSISTANT`, `SYSTEM`, `INTERNAL` |
| `content` | `str` | Message text |
| `file_ids` | `List[str]` | IDs of attached artifacts |
| `inline_args` | `dict` | Extracted inline arguments from content |
| `created_at` | `float` | Unix timestamp |
| `updated_at` | `float` | Unix timestamp |

Thread-safe methods for streaming: `safe_append_content(chunk)`, `safe_update_content(text)`, `safe_get_content()`.

### ConversationSettings

| Field | Type | Default |
|---|---|---|
| `streaming` | `bool` | `True` |
| `text_settings` | `dict` | `{}` (keys like `max_tokens`, `temperature`) |
| `image_settings` | `dict` | `{}` (keys like `width`, `height`, `steps`) |

### Mutation Methods

Every mutation emits exactly one `DomainEvent` (recorded + dispatched):

| Method | EventType | Description |
|---|---|---|
| `add_message(speaker, content, ...)` | `MESSAGE_CREATED` | Appends to tree, updates `active_head_id` |
| `update_message(id, content?, file_ids?)` | `MESSAGE_UPDATED` | In-place content fix |
| `delete_message(id)` | `MESSAGE_DELETED` | Removes from tree |
| `stream_message(id, content, append, end)` | `MESSAGE_STREAM_START` / `MESSAGE_STREAM_END` | Streaming updates (silent for intermediate chunks) |
| `attach_file(message_id, file_id)` | `ATTACHMENT_ADDED` | Link artifact to message |
| `detach_file(message_id, file_id)` | `ATTACHMENT_REMOVED` | Unlink artifact from message |
| `change_title(new_title)` | `TITLE_CHANGED` | Update title |
| `change_prompt(new_prompt)` | `PROMPT_CHANGED` | Update system prompt |
| `update_settings(settings)` | `SETTINGS_UPDATED` | Merge setting changes |

---

## Domain Events

Defined in `claia.lib.data.events`. Events serve as both the persisted audit trail and runtime notification system.

### EventType Enum

```python
class EventType(Enum):
    CONVERSATION_CREATED
    MESSAGE_CREATED
    MESSAGE_UPDATED
    MESSAGE_DELETED
    MESSAGE_STREAM_START
    MESSAGE_STREAM_END
    ATTACHMENT_ADDED
    ATTACHMENT_REMOVED
    TITLE_CHANGED
    PROMPT_CHANGED
    SETTINGS_UPDATED
```

### DomainEvent

| Field | Type | Description |
|---|---|---|
| `event_type` | `EventType` | What happened |
| `entity_id` | `str` | ID of the affected entity (conversation or message) |
| `entity_type` | `str` | Always `"conversation"` for now |
| `event_id` | `str` | Unique event UUID |
| `parent_id` | `str \| None` | Parent entity (e.g. message's parent in tree) |
| `timestamp` | `float` | When it happened |
| `metadata` | `dict` | Event-specific payload |

### How Events Flow

```
Conversation.add_message("user", "hello")
    │
    ├──► self.events.append(event)      # persisted audit trail
    ├──► self._pending_events.append()  # transient queue for runtime
    └──► for listener in listeners:     # real-time callbacks
             listener(event)
```

**Runtime consumption pattern:**

```python
# Poll-based (CLI uses this)
pending = conversation.pull_events()  # returns + clears pending
if pending:
    store.save(conversation)

# Listener-based (API might use this)
def on_event(event: DomainEvent):
    db.handle(event)

conversation.add_event_listener(on_event)
```

### Serialization

Events are included in `conversation.to_dict()["events"]` and restored by `Conversation.from_dict()`. The full event history travels with the conversation.

---

## Serialized Conversation Structure

What `conversation.to_dict()` produces (and what gets saved as JSON / sent over the API):

```json
{
  "id": "uuid",
  "name": "conversation-uuid",
  "media_type": "application/json",
  "size": 0,
  "is_reference": false,
  "source_uri": null,
  "metadata": {"title": "My Chat", "encoding": "utf-8"},
  "created_at": 1710000000.0,
  "updated_at": 1710000000.0,
  "encoding": "utf-8",
  "title": "My Chat",
  "prompt": {"system": "You are a helpful assistant."},
  "active_head_id": "msg-uuid-2",
  "messages": [
    {
      "message_id": "msg-uuid-1",
      "parent_id": null,
      "speaker": "user",
      "content": "hello",
      "file_ids": [],
      "created_at": 1710000000.0,
      "updated_at": 1710000000.0,
      "inline_args": {}
    },
    {
      "message_id": "msg-uuid-2",
      "parent_id": "msg-uuid-1",
      "speaker": "assistant",
      "content": "Hi! How can I help?",
      "file_ids": [],
      "created_at": 1710000001.0,
      "updated_at": 1710000001.0,
      "inline_args": {}
    }
  ],
  "events": [
    {
      "event_id": "evt-uuid",
      "event_type": "CONVERSATION_CREATED",
      "entity_type": "conversation",
      "entity_id": "uuid",
      "parent_id": null,
      "timestamp": 1710000000.0,
      "metadata": {"title": "My Chat", "system_prompt": "You are a helpful assistant."}
    }
  ],
  "settings": {
    "streaming": true,
    "text_settings": {},
    "image_settings": {}
  }
}
```

---

## CLI Storage (JsonStore)

Located in `claia.cli.storage`. A minimal JSON-file-based store used only by the CLI runtime. Not part of the core library.

```python
from claia.cli.storage import JsonStore

store = JsonStore("/path/to/data")
store.save(conversation)           # writes conversations/{id}.json
loaded = store.load(conv_id)       # reads from any subdirectory
store.delete(conv_id)              # removes the JSON file
store.list_all(artifact_type="conversations")  # lists all JSON metadata
```

Disk layout:

```
/path/to/data/
  ├── conversations/  {id}.json
  ├── prompts/        {id}.json
  ├── texts/          {id}.json
  ├── images/         {id}.json
  └── audio/          {id}.json
```

The store adds an `artifact_type` field to the JSON for rehydration on load. Writes are atomic (temp file + rename).

---

## Guidance for the Slate API

When building the API layer on top of these models:

### Database Schema

The serialized dict structure maps naturally to a normalized schema:

- **conversations** table: `id`, `title`, `prompt` (JSON), `active_head_id`, `settings` (JSON), `created_at`, `updated_at`
- **messages** table: `message_id`, `conversation_id` (FK), `parent_id`, `speaker`, `content`, `file_ids` (JSON array), `inline_args` (JSON), `created_at`, `updated_at`
- **events** table: `event_id`, `conversation_id` (FK), `event_type`, `entity_id`, `parent_id`, `timestamp`, `metadata` (JSON)

Alternatively, for simpler deployments, the entire `to_dict()` output can be stored as a single JSON column.

### Event-Driven Persistence

The API can use event listeners for real-time database writes:

```python
conv = Conversation.from_dict(db_data)

def persist_event(event: DomainEvent):
    db.insert_event(conv.id, event.to_dict())
    if event.event_type == EventType.MESSAGE_CREATED:
        db.insert_message(conv.id, event.metadata)
    # etc.

conv.add_event_listener(persist_event)
```

Or use the poll pattern after request handling:

```python
conv.add_message("user", request.content)
result = await agent.run(conv)

for event in conv.pull_events():
    db.record(event)
db.save_conversation(conv)
```

### API Responses

`to_dict()` output is already JSON-serializable and can be returned directly from API endpoints. For list endpoints, only the top-level fields (without messages/events) would typically be returned.

---

## File Map

```
claia/lib/data/
  __init__.py              — re-exports all models + events
  events.py                — EventType enum + DomainEvent dataclass
  models/
    __init__.py            — re-exports all model classes
    base.py                — BaseArtifact (ABC)
    text.py                — TextArtifact
    image.py               — ImageArtifact
    audio.py               — AudioArtifact
    prompt.py              — Prompt
    conversation/
      __init__.py          — re-exports Conversation, Message, ConversationSettings
      conversation.py      — Conversation (main model)
      message.py           — Message
      conversation_settings.py — ConversationSettings
  utils/
    image.py               — image processing utilities
    text.py                — text processing utilities
    tool_text.py           — tool call text utilities

claia/cli/storage/
  __init__.py              — exports JsonStore
  json_store.py            — JsonStore (CLI-only file persistence)
```
