# Integration Plan

This document describes the target architecture for claia, the split into a
library and a framework, the conversation/streaming persistence design, and the
evolution of the plugin system. Reasoning, options considered, and deferred
decisions are captured in `integration-thoughts.md`.

## Executive Summary

claia is being restructured from a single package into three coordinated
packages that live in one repository:

- **`claia_core`** — the library. Pure data models, serialization, and concrete
  implementations of model architectures, deployments, solvers, and tools.
  Importable and usable with no framework, no inversion of control, no
  pluggy dependency.
- **`claia`** — the framework. Plugin discovery and lifecycle via pluggy, the
  `Registry` composition root, `Process`/worker execution model, agent
  orchestration, and configuration plumbing.
- **`claia_cli`** — the command-line application built on top of the framework.

This split preserves the flexibility that drove the project (users can compose
claia_core components directly) while keeping the "easy mode" framework
experience for users who want an opinionated system. Slate (and any future
applications) consume claia_core and claia as dependencies.

Alongside the split, the `Conversation` model gains a single-callback observer
API, streaming persistence adopts a batched-flush pattern, and the plugin
system evolves to support richer parameter declarations, modality awareness,
and lazy loading.

## Target Architecture

### Package Layout

```
/workspaces/claia/
├── src/
│   ├── claia_core/              # Library — no IoC, no pluggy
│   │   ├── data/
│   │   │   ├── conversation.py
│   │   │   ├── message.py
│   │   │   ├── events.py
│   │   │   └── settings.py
│   │   ├── architectures/
│   │   │   ├── base.py          # BaseArchitecture ABC
│   │   │   ├── openai.py
│   │   │   ├── anthropic.py
│   │   │   └── transformers.py
│   │   ├── deployments/
│   │   │   ├── base.py          # BaseDeployment ABC
│   │   │   ├── api.py
│   │   │   ├── local.py
│   │   │   ├── remote.py
│   │   │   └── dummy.py
│   │   ├── solvers/
│   │   │   ├── base.py
│   │   │   └── default.py
│   │   ├── definitions/
│   │   │   ├── model_definition.py
│   │   │   └── builtin.py
│   │   ├── tools/
│   │   │   ├── patterns/
│   │   │   ├── protocols/
│   │   │   └── modules/
│   │   ├── plugins/             # Plugin metadata types (ParamSpec, ExtensionInfo)
│   │   │   └── base.py
│   │   └── modality.py          # Modality enum, GenerationChunk
│   │
│   ├── claia/                   # Framework — pluggy, lifecycle
│   │   ├── hooks/               # Hookspecs (thin wrappers over ABCs)
│   │   ├── manager.py           # PluginManager + discovery + lazy loading
│   │   ├── registry.py          # Composition root
│   │   ├── process.py           # Process, ProcessQueue, workers
│   │   └── agents/
│   │       ├── base.py
│   │       └── simple.py
│   │
│   └── claia_cli/               # CLI application
│       ├── __main__.py
│       ├── commands/
│       ├── agents.py            # WriterAgent (programmatically registered)
│       ├── storage.py           # JsonStore
│       └── settings.py
└── tests/
    ├── claia_core/
    ├── claia/
    └── claia_cli/
```

### Dependency Direction

Strict, one-way:

```
claia_cli  →  claia  →  claia_core
```

If `claia_core` ever needs something from `claia`, that's a signal the thing
belongs in `claia_core` instead.

### Packaging

- Each package has its own `pyproject.toml`.
- Versions are synchronized across all three packages until external users of
  `claia_core` alone emerge.
- Entry points for built-in plugins are declared in `claia_core`'s
  `pyproject.toml` (they register under `claia.*` groups that the framework
  consumes). This is conventional — entry points are passive metadata until
  something asks for them.

## The Conversation Model (claia_core)

The `Conversation` is the universal data carrier for input to and output from
AI models. It holds messages as a flat list; tree structure is implicit via
`parent_id` pointers on each message. The current "linear thread" used by LLM
backends is computed on demand by walking `parent_id` from `active_head_id`
back to the root.

### Structure

```python
class Message:
    id: str
    parent_id: Optional[str]
    speaker: str
    content: str
    file_ids: List[str]
    inline_args: Dict[str, Any]
    created_at: float
    updated_at: float

class DomainEvent:
    event_id: str
    event_type: EventType
    entity_type: str
    entity_id: str
    parent_id: Optional[str]
    timestamp: float
    metadata: Dict[str, Any]

class Conversation:
    id: str
    title: str
    messages: List[Message]
    events: List[DomainEvent]
    active_head_id: Optional[str]
    settings: ConversationSettings
    _pending_events: List[DomainEvent]
    _on_event: Optional[EventCallback]
```

### Observer API

A single optional callback is invoked on every domain event. The callback
receives the event and, when applicable, the related message.

```python
EventCallback = Callable[[DomainEvent, Optional[Message]], None]

class Conversation:
    def __init__(self, ..., on_event: Optional[EventCallback] = None): ...
    def observe(self, on_event: EventCallback) -> None: ...
```

**Event-to-message contract** (documented for integrators):

| Event                    | message argument                             |
|--------------------------|----------------------------------------------|
| `MESSAGE_CREATED`        | the new message                              |
| `MESSAGE_UPDATED`        | post-mutation state                          |
| `MESSAGE_DELETED`        | state just before deletion                   |
| `MESSAGE_STREAM_START`   | the empty message being streamed into        |
| `MESSAGE_STREAM_END`     | final state                                  |
| `CONVERSATION_UPDATED`   | `None` (conversation-level metadata change)  |

Observer failures are caught and logged; they never corrupt conversation state.
Observers are expected to handle their own errors.

### Streaming Mutations Do Not Fire Observers

`append_stream_chunk(message_id, chunk)` appends to a message's content without
emitting events or invoking observers. Per-chunk notifications would flood the
event log and the callback. Content flushes during streaming are handled
explicitly by the application (see Streaming Persistence below) rather than
through observers.

### Serialization Helpers

- `to_dict()` / `from_dict()` — full monolithic serialization (JSON-friendly).
- `messages_to_rows()` — list of flat dicts, relational-friendly.
- `events_to_rows()` — list of flat dicts, relational-friendly.
- `pull_events()` — retained as an alternative to observers for pull-based
  integrators (like the CLI's `JsonStore`). Observers and `pull_events` are
  documented as alternative patterns; an application should use one or the
  other, not both.

## Streaming Persistence

### Strategy: Option 1 — Batched Synchronous Flush

Applications flush to the database at regular intervals during streaming,
balancing resilience (bounded data loss on crash) against performance
(acceptable number of DB commits per response).

### The Two-Function Split (slate)

Structural changes and content growth are persisted via different code paths
because they have different costs and call frequencies.

```python
# slate/services/ai.py

def load_claia_conv_observed(db_session, db_conv) -> ClaiaConversation:
    """Load and attach a DB observer. Mutations automatically stage DB
    operations via the session; caller commits at appropriate boundaries."""
    ...

def flush_streaming_content(db_session, message_id, claia_conv) -> None:
    """Targeted UPDATE of a single in-progress message's content.
    Called at flush intervals during streaming. Not observer-driven because
    append_stream_chunk intentionally does not fire observers."""
    ...
```

### End-to-End Flow

1. User sends message → slate endpoint.
2. slate loads `claia_conv` with an attached DB observer.
3. slate calls `claia_conv.add_message(USER, text)` — observer stages the new
   AIMessage and AIEvent in the DB session. slate commits.
4. slate submits a `Process` to the framework's queue and returns an SSE
   response.
5. A worker picks up the process. The agent calls
   `claia_conv.start_streaming_message(ASSISTANT)`. The observer stages the
   empty message and stream_start event. Process emits `stream_start`.
6. slate's SSE generator receives `stream_start` from the process event queue
   and commits. The empty assistant row exists in the DB.
7. For each token, the agent calls `claia_conv.append_stream_chunk(...)` (no
   observer fire) and emits a `token` event. slate's generator forwards the
   token to the client and accumulates a character count.
8. When characters exceed a threshold (~80 chars) or time elapses (~250ms),
   slate calls `flush_streaming_content` and commits. Targeted UPDATE only.
9. On `stream_end`, the observer stages the STREAM_END event. slate runs a
   final `flush_streaming_content` and commits. SSE sends `done`.
10. On `stream_error`, slate flushes whatever content arrived, stages the
    error state, commits, and sends an error SSE event.

### Concurrency

- Worker thread mutates `claia_conv` (calls `append_stream_chunk`) and emits
  process events into a queue.
- Request (SSE) thread reads `claia_conv` state at flush points and owns all
  DB access. `g.db_session` stays in the request thread.
- Under CPython's GIL, content reads during streaming may be slightly stale
  but never inconsistent. No locking needed.

### Tunable Parameters

- `FLUSH_EVERY_CHARS` (default ~80) — flush after this many characters.
- `FLUSH_EVERY_MS` (default ~250) — flush after this many milliseconds since
  the last flush.

Worst-case data loss on crash is bounded by these thresholds.

## Plugin System Evolution

### Pluggy Stays in claia

`claia_core` has no pluggy dependency. Plugin contracts are expressed as
abstract base classes (ABCs) in `claia_core` (e.g., `BaseArchitecture`,
`BaseDeployment`, `BaseSolver`). The framework's hookspecs in `claia` mirror
the ABC signatures — two complementary contracts:

- The ABC answers: *what methods must an implementation provide?*
- The hookspec answers: *how does the plugin system discover and dispatch to
  implementations?*

Third parties implement the ABCs and register via entry points. They never
need to know pluggy exists.

### ParamSpec Replaces `required_args`

Structured parameter declarations replace the loose `List[str]` used today.

```python
class ParamScope(Enum):
    INIT = "init"        # Passed at plugin construction (credentials, config)
    RUNTIME = "runtime"  # Passed per call (generation params)

@dataclass
class ParamSpec:
    name: str
    type: type = str
    scope: ParamScope = ParamScope.RUNTIME
    required: bool = False
    default: Any = None
    description: str = ""
    choices: Optional[List[Any]] = None
    secret: bool = False   # Hint to Settings/CLI not to log this

@dataclass
class ExtensionInfo:
    name: str
    title: str
    description: str
    params: List[ParamSpec] = field(default_factory=list)
```

**What this unlocks:**

- Settings can auto-generate CLI flags, env vars, and validation from the
  schema. No more hand-maintaining `CONFIG_VARS`.
- Clean init vs. runtime separation — Manager knows what to pass to
  `__init__` vs. what to forward to generation calls.
- Third-party plugins are self-documenting; `claia inspect <plugin>` is a
  natural feature.
- Secret handling is explicit — credentials are masked in logs.
- Type validation at the boundary.

### Modality as a First-Class Concept

`ModelDefinition` gains modality declarations:

```python
class Modality(Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    EMBEDDING = "embedding"

@dataclass
class ModelDefinition:
    # ... existing fields ...
    input_modalities: List[Modality] = field(default_factory=lambda: [Modality.TEXT])
    output_modalities: List[Modality] = field(default_factory=lambda: [Modality.TEXT])
    supports_streaming: bool = True
    supports_tools: bool = False
    supports_system_prompt: bool = True
```

Existing text-only definitions default to `TEXT` → `TEXT`. New modalities are
purely additive.

### GenerationChunk for Multi-Modal Output

Deployment hooks currently return `Iterator[str]`. This becomes
`Iterator[GenerationChunk]`:

```python
class ChunkKind(Enum):
    TEXT = "text"
    IMAGE_BYTES = "image_bytes"
    AUDIO_BYTES = "audio_bytes"
    VIDEO_BYTES = "video_bytes"
    PROGRESS = "progress"
    DONE = "done"

@dataclass
class GenerationChunk:
    kind: ChunkKind
    data: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
```

Text models wrap their tokens in `TEXT` chunks. Image generation yields
`IMAGE_BYTES`. Video can yield progressive frames. Consumers dispatch on
`chunk.kind`.

### Two-Phase Plugin Loading (Lazy)

**Phase 1: Metadata discovery (on startup)**

Iterate entry points, import each module, read the class's `info` attribute,
record a `PluginEntry` with the class reference but no instance.

**Phase 2: Instantiation (on first use)**

When a plugin is first needed, instantiate it with filtered kwargs from
Settings (only the `INIT`-scoped params it declared). Cache the instance.

This requires a convention: **plugins must not do expensive work at import or
class-definition time**. Class-level `info = ArchitectureInfo(...)` is fine;
expensive setup happens in `__init__`.

### Security: Explicit Param Declaration

Plugins can only receive kwargs they've declared via ParamSpec. A plugin that
wants credentials must declare them in its `info.params` list, making any
attempt to harvest secrets visible in the plugin's metadata. Additional
measures:

- Secret parameters are logged at INFO level during plugin discovery. Installing
  a new plugin that requests secrets produces visible startup output.
- `claia inspect <plugin>` (future) shows the full param list for audit.

## Migration Roadmap

The work is organized into phases that can be executed sequentially. Each
phase produces a working system — you can pause after any phase.

### Phase 1: Package Restructure (mostly mechanical)

- Create `src/claia_core/`, `src/claia_cli/`, separate `pyproject.toml` files.
- Move data models, architectures, deployments, solvers, definitions, tool
  implementations into `claia_core`.
- Move CLI code into `claia_cli`.
- `src/claia/` slims down to hookspecs, Manager, Registry, Process, agents.
- Declare ABCs in `claia_core` for each plugin type. Hookspecs in `claia`
  mirror the ABCs.
- Move entry points to `claia_core`'s `pyproject.toml`.
- Update slate's imports: `claia.lib.data` → `claia_core.data`, etc.
- Drop the unused `aia` dependency.

### Phase 2: Conversation Observer + slate Integration

- Add the `on_event` callback to `Conversation`.
- Route all mutation methods through the internal `_record(event, message)`
  helper that appends to `_pending_events` and invokes `_on_event`.
- Add `load_claia_conv_observed()` to slate's `services/ai.py`.
- Add `flush_streaming_content()` to slate.
- Replace slate's streaming HTTP endpoint with the SSE flow described above.
- Keep `pull_events()` available for pull-based consumers.

### Phase 3: ParamSpec Evolution

- Define `ParamSpec` and `ParamScope` in `claia_core/plugins/base.py`.
- Update `ExtensionInfo` to use `params: List[ParamSpec]` (replacing
  `required_args`).
- Update Manager to consume the new format: filter kwargs by scope=INIT for
  `__init__`, validate/forward scope=RUNTIME for generation calls.
- Migrate built-in plugins to declare ParamSpecs.
- Update Settings to build its var list from ParamSpec metadata rather than
  a hand-maintained `CONFIG_VARS`.

### Phase 4: Modality + GenerationChunk

- Add `Modality` enum and `GenerationChunk` types to `claia_core/modality.py`.
- Extend `ModelDefinition` with modality fields (defaults preserve current
  behavior).
- Change the Deployment hook signature from `Iterator[str]` to
  `Iterator[GenerationChunk]`. Text deployments wrap tokens in TEXT chunks.
- Update the Registry's streaming API to expose chunks to consumers. For
  text-only use, add a convenience that flattens TEXT chunks back to strings.
- Declare modalities on built-in model definitions.

### Phase 5: Lazy Plugin Loading

- Refactor Manager to discover plugin metadata without instantiating classes.
- Introduce `PluginEntry` (class ref + info + optional instance).
- Defer instantiation to first use.
- Add logging for plugin discovery (especially secret params).

### Later / Deferred

- Cross-cutting hooks (usage tracking, rate-limit detection, error
  classification, caching) — introduce when two or more concrete use cases
  exist.
- Wrapper plugins (middleware pattern) — introduce when a third-party wants to
  ship one.
- Plugin identifier namespacing (reverse-DNS or similar) — revisit when
  third-party plugin ecosystem grows.
- Pydantic-based plugin config schemas — consider if ParamSpec grows
  unwieldy or if richer validation is needed.
- Webapp and worker packages — out of scope for this plan.

## Testing Strategy

- Each package has its own `tests/` directory.
- `claia_core` tests are pure — no pluggy, no plugin loading, no framework.
- `claia` tests exercise real pluggy discovery, the Registry, Process flow.
- `claia_cli` tests exercise command routing, JsonStore, CLI-specific agents.
- Shared test fixtures (common conversation shapes, dummy models) live in a
  repo-level `tests/fixtures/` or are duplicated between suites if small.
  Don't over-engineer this.

## Documentation Approach

- Each package ships a `README.md` with focused scope and examples.
- `claia_core` README: library usage, data models, how to implement plugins.
- `claia` README: framework usage, Registry, Process, agents.
- `claia_cli` README: end-user CLI guide.
- The observer contract (event → message mapping) is documented in
  `claia_core/data/conversation.py` docstrings.
- ParamSpec patterns for secret handling and audit are documented alongside
  the plugin system docs.

## Decisions Log

| Decision | Chosen | Rationale |
|----------|--------|-----------|
| Architecture style | Library + framework split (three packages) | Preserves flexibility of a library while keeping opinionated framework convenience |
| Repo layout | Monorepo, coordinated versions | Simpler until external users diverge |
| Conversation structure | List of messages with `parent_id`, tree implicit | Simple, existing, no new abstractions |
| Mutation notifications | Observer (`on_event` callback) | Real-time, push-based, standard pattern |
| Multi-observer support | Single observer for now | Simpler; add later if needed |
| Per-chunk observer fire | No — `append_stream_chunk` silent | Avoids event flooding |
| Streaming persistence | Batched synchronous flush (Option 1) | Best tradeoff for current scale |
| Content flush mechanism | Targeted function, not observer | Keeps observer API clean; explicit control |
| `pull_events()` fate | Kept as alternative | Non-breaking, useful for pull-based consumers |
| Pluggy location | Framework only | Library stays dependency-light |
| Plugin contracts | ABCs in `claia_core`, hookspecs in `claia` | Two different concerns, both explicit |
| Plugin metadata | Custom `ParamSpec` (not Pydantic) | Avoids core dependency; can upgrade later |
| Plugin identifiers | Friendly names only for now | Deferred reverse-DNS/namespacing discussion |
| Plugin loading | Two-phase (metadata eager, instance lazy) | Startup performance + plays well with ParamSpec |
| Plugin security | Explicit ParamSpec declarations | Principle of least privilege |
| Output type | `GenerationChunk` stream | Unifies text/image/audio/video |
| Backward compatibility | Coordinate updates, no shims | Internal project; slate is the only consumer |
| CLI `WriterAgent` | Stays programmatically registered in `claia_cli` | CLI-specific, not distributable |
| `aia` dependency | Remove | Unused since early refactor |

## Open Questions / Future Work

- **Plugin identifier namespacing** — deferred; likely reverse-DNS or similar
  when the plugin ecosystem grows.
- **Multiple observer support** — add if a concrete use case appears (e.g.,
  websocket broadcast alongside DB persistence).
- **Stream resumption after crash** — the current design bounds data loss but
  does not resume interrupted streams. If resumption becomes a requirement,
  consider a write-ahead chunk table or durable message queue.
- **Cost/usage tracking** — will likely become a cross-cutting pluggy hook
  once multiple providers need it.
- **Webapp worker package** — scoped for a future iteration.
