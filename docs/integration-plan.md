# Integration Plan

This document describes the target architecture for claia, the split into
a library, framework, and CLI under a shared namespace, the
conversation/streaming persistence design, and the evolution of the
plugin system. Reasoning, options considered, and deferred decisions are
captured in `integration-thoughts.md`.

## Executive Summary

claia is being restructured from a single package into three coordinated
subpackages that share the `claia` namespace and live in one repository:

- `**claia.core**` — the library. Pure data models, serialization, and
concrete implementations of model architectures, deployments, solvers,
and tools. Importable and usable with no framework, no inversion of
control, no pluggy dependency.
- `**claia.framework**` — the orchestration runtime. Plugin discovery
and lifecycle via pluggy, the `Registry` composition root,
`Process`/worker execution model, agent orchestration, and
configuration plumbing. Also serves as the convenience hub:
re-exports the most commonly used types from `claia.core` so callers
can write `from claia.framework import Registry, Conversation, Result`.
- `**claia.cli**` — the command-line application built on top of the
framework.

`claia` itself is an **implicit (PEP 420) namespace package** — there is
**no `claia/__init__.py`** anywhere. Each subpackage is independently
installable as its own distribution, but during the monorepo phase all
three ship from a single `pyproject.toml`.

This split preserves the flexibility that drove the project (users can
compose `claia.core` components directly) while keeping the "easy mode"
framework experience for users who want an opinionated system. Slate
(and any future applications) consume `claia.core` and `claia.framework`
as dependencies.

Alongside the split, the `Conversation` model gains a single-callback
observer API, streaming persistence adopts a batched-flush pattern, and
the plugin system evolves to support richer parameter declarations,
modality awareness, and lazy loading.

## Target Architecture

### Package Layout

```
/workspaces/claia/
├── pyproject.toml              # Single file during monorepo phase
└── src/
    └── claia/                  # PEP 420 namespace — NO __init__.py here
        ├── core/               # Library — no IoC, no pluggy
        │   ├── __init__.py     # Re-exports core data + plugin metadata
        │   ├── data/
        │   │   ├── models/conversation/
        │   │   ├── events.py
        │   │   └── ...
        │   ├── architectures/
        │   │   ├── base.py     # BaseArchitecture ABC
        │   │   ├── openai.py
        │   │   ├── anthropic.py
        │   │   └── ...
        │   ├── deployments/
        │   │   ├── base.py     # BaseDeployment ABC
        │   │   ├── api.py
        │   │   ├── local.py
        │   │   ├── remote.py
        │   │   └── dummy.py
        │   ├── solvers/
        │   │   ├── base.py
        │   │   └── default.py
        │   ├── definitions/
        │   │   ├── model_definition.py
        │   │   └── ...
        │   ├── tools/
        │   │   ├── patterns/
        │   │   ├── protocols/
        │   │   └── modules/
        │   ├── plugins/
        │   │   └── base.py     # ExtensionInfo + per-plugin *Info dataclasses
        │   ├── enums/
        │   ├── models/         # BaseModel + concrete implementations
        │   └── results.py
        │
        ├── framework/          # Framework — pluggy, lifecycle
        │   ├── __init__.py     # Convenience hub (re-exports from claia.core)
        │   ├── hooks/          # Hookspecs (thin wrappers over ABCs)
        │   ├── manager.py      # PluginManager + discovery + lazy loading
        │   ├── registry.py     # Composition root
        │   ├── process.py      # Process
        │   ├── queue.py        # ProcessQueue
        │   └── agents/
        │       ├── base.py
        │       └── simple.py
        │
        └── cli/                # CLI application
            ├── __init__.py
            ├── __main__.py     # Console entry point
            ├── commands/
            ├── agents.py       # WriterAgent (programmatically registered)
            ├── storage/        # JsonStore
            └── settings.py
└── src/tests/
    ├── core/
    ├── framework/
    └── cli/
```

### Why a Namespace Package

We considered four shapes for the package boundary:

1. **Flat top-level packages** (`claia_core`, `claia`, `claia_cli`) —
  easy to split later but reads as three unrelated projects and the
   bare `claia` name asymmetrically claims the framework layer.
2. **Single regular package with subpackages** (`claia.core`,
  `claia.framework`, `claia.cli`) — beautiful imports but cannot ship
   `claia.core` standalone without dragging in the rest of the tree.
3. `**sys.modules` shim** (`claia_core` plus a runtime alias making
  `claia.core` resolve to it) — works but creates two names for the
   same module objects, breaks type checkers, and is fragile.
4. **PEP 420 namespace** (`claia.core`, `claia.framework`, `claia.cli`
  under a namespace `claia` with no top-level `__init__.py`) — chosen.

The namespace approach gives us hierarchical imports today and clean
distributability tomorrow without any runtime hacks. The cost is a
genuinely empty `claia` namespace — we cannot put a docstring,
re-exports, or a `__version__` at the bare `claia` level. We recover
the convenience-hub experience one level down by making
`claia/framework/__init__.py` a deliberately rich re-export surface.

### Dependency Direction

Strict, one-way:

```
claia.cli  →  claia.framework  →  claia.core
```

If `claia.core` ever needs something from `claia.framework`, that's a
signal the thing belongs in `claia.core` instead.

### Packaging

- **Single `pyproject.toml`** during the monorepo phase. Per-layer
optional dependencies (extras) are declared so the boundaries are
visible:
  ```toml
  [project.optional-dependencies]
  core = ["requests", "python-dotenv", "beautifulsoup4", "chardet<6"]
  framework = ["pluggy"]
  cli = ["pyfiglet", "pyreadline3"]
  ```
- The default install pulls all three layers' deps under
`[project.dependencies]` so the CLI experience works out of the box.
- `[tool.setuptools.packages.find]` is configured with
`namespaces = true` and `include = ["claia*"]` so setuptools
discovers the subpackages without requiring a top-level
`__init__.py`.
- Console script: `claia = "claia.cli.__main__:main"`.
- Plugin entry points are declared in this single `pyproject.toml`
today. Group names remain `claia.architectures`,
`claia.deployments`, `claia.solvers`, `claia.definitions`,
`claia.tool_protocols`, `claia.tool_modules`, `claia.agents`
— these are stable identifiers, not module paths, and external
plugins keep registering against them unchanged. The
`claia.tool_patterns` group was retired in the tools overhaul
phase 7 (see `docs/tools-overhaul-plan.md`); the streaming
`claia.core.parser.TagParser` replaces the per-pattern detector
plumbing.
- When the repo splits into separate distributions, each subpackage
takes its own `pyproject.toml` and continues to ship under the same
`claia.*` namespace. Entry-point declarations move with the
subpackage that owns the implementation (e.g., the `claia.core.*`
plugin entries move to `claia-core`'s `pyproject.toml`).

### The Convenience Hub at `claia.framework`

Because `claia` itself has no `__init__.py`, the umbrella experience
moves one level down:

```python
from claia.framework import Registry, Process, ProcessQueue
from claia.framework import Conversation, Message, Result
from claia.framework import BaseAgent
```

Pure-library users skip the framework entirely:

```python
from claia.core.data import Conversation, Message
from claia.core.results import Result
```

CLI extension authors import from `claia.cli` (which itself re-exports
from both `claia.core` and `claia.framework`):

```python
from claia.cli import Registry, Conversation
from claia.cli.commands.base import Command
```

## The Conversation Model (claia.core)

The `Conversation` is the universal data carrier for input to and output
from AI models. It holds messages as a flat list; tree structure is
implicit via `parent_id` pointers on each message. The current "linear
thread" used by LLM backends is computed on demand by walking
`parent_id` from `active_head_id` back to the root.

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
    _pending_events: List[DomainEvent]
    _on_event: Optional[EventCallback]
```

> The old `settings: ConversationSettings` field was removed in Phase 3.
> Generation parameters (`temperature`, `max_tokens`, ...) are declared by
> model/architecture plugins via `ParamSpec(scope=RUNTIME)` and flow
> through `Process.parameters` / `registry.run(**kwargs)`, not through
> the `Conversation` object.

### Observer API

A single optional callback is invoked on every domain event. The
callback receives the event and, when applicable, the related message.

```python
EventCallback = Callable[[DomainEvent, Optional[Message]], None]

class Conversation:
    def __init__(self, ..., on_event: Optional[EventCallback] = None): ...
    def observe(self, on_event: EventCallback) -> None: ...
```

**Event-to-message contract** (documented for integrators):


| Event                  | message argument                            |
| ---------------------- | ------------------------------------------- |
| `MESSAGE_CREATED`      | the new message                             |
| `MESSAGE_UPDATED`      | post-mutation state                         |
| `MESSAGE_DELETED`      | state just before deletion                  |
| `MESSAGE_STREAM_START` | the empty message being streamed into       |
| `MESSAGE_STREAM_END`   | final state                                 |
| `CONVERSATION_UPDATED` | `None` (conversation-level metadata change) |


Observer failures are caught and logged; they never corrupt
conversation state. Observers are expected to handle their own errors.

### Streaming Mutations Do Not Fire Observers

`append_stream_chunk(message_id, chunk)` appends to a message's content
without emitting events or invoking observers. Per-chunk notifications
would flood the event log and the callback. Content flushes during
streaming are handled explicitly by the application (see Streaming
Persistence below) rather than through observers.

### Serialization Helpers

- `to_dict()` / `from_dict()` — full monolithic serialization
(JSON-friendly).
- `messages_to_rows()` — list of flat dicts, relational-friendly.
- `events_to_rows()` — list of flat dicts, relational-friendly.
- `pull_events()` — retained as an alternative to observers for
pull-based integrators (like the CLI's `JsonStore`). Observers and
`pull_events` are documented as alternative patterns; an application
should use one or the other, not both.

## Streaming Persistence

### Strategy: Option 1 — Batched Synchronous Flush

Applications flush to the database at regular intervals during
streaming, balancing resilience (bounded data loss on crash) against
performance (acceptable number of DB commits per response).

### The Two-Function Split (slate)

Structural changes and content growth are persisted via different code
paths because they have different costs and call frequencies.

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
3. slate calls `claia_conv.add_message(USER, text)` — observer stages
  the new AIMessage and AIEvent in the DB session. slate commits.
4. slate submits a `Process` to the framework's queue and returns an
  SSE response.
5. A worker picks up the process. The agent calls
  `claia_conv.start_streaming_message(ASSISTANT)`. The observer
   stages the empty message and stream_start event. Process emits
   `stream_start`.
6. slate's SSE generator receives `stream_start` from the process
  event queue and commits. The empty assistant row exists in the DB.
7. For each token, the agent calls `claia_conv.append_stream_chunk(...)`
  (no observer fire) and emits a `token` event. slate's generator
   forwards the token to the client and accumulates a character count.
8. When characters exceed a threshold (~80 chars) or time elapses
  (~250ms), slate calls `flush_streaming_content` and commits.
   Targeted UPDATE only.
9. On `stream_end`, the observer stages the STREAM_END event. slate
  runs a final `flush_streaming_content` and commits. SSE sends
   `done`.
10. On `stream_error`, slate flushes whatever content arrived, stages
  the error state, commits, and sends an error SSE event.

### Concurrency

- Worker thread mutates `claia_conv` (calls `append_stream_chunk`) and
emits process events into a queue.
- Request (SSE) thread reads `claia_conv` state at flush points and
owns all DB access. `g.db_session` stays in the request thread.
- Under CPython's GIL, content reads during streaming may be slightly
stale but never inconsistent. No locking needed.

### Tunable Parameters

- `FLUSH_EVERY_CHARS` (default ~80) — flush after this many characters.
- `FLUSH_EVERY_MS` (default ~250) — flush after this many milliseconds
since the last flush.

Worst-case data loss on crash is bounded by these thresholds.

## Plugin System Evolution

### Pluggy Stays in `claia.framework`

`claia.core` has no pluggy dependency in its public contract. Plugin
contracts are expressed as abstract base classes (ABCs) in `claia.core`
(e.g., `BaseArchitecture`, `BaseDeployment`, `BaseSolver`). The
framework's hookspecs in `claia.framework.hooks` mirror the ABC
signatures — two complementary contracts:

- The ABC answers: *what methods must an implementation provide?*
- The hookspec answers: *how does the plugin system discover and
dispatch to implementations?*

The plugin metadata dataclasses themselves (`ExtensionInfo`,
`ArchitectureInfo`, `DeploymentInfo`, etc.) live in
`claia.core.plugins.base` so plugin implementations can construct them
without depending on the framework.

> **Phase-1 caveat:** the built-in plugin classes shipped today in
> `claia.core.architectures.`*, `claia.core.deployments.*`, etc. still
> import `pluggy.HookimplMarker` to register their hook implementations
> directly. The cleanest fix is for `claia.framework` to provide thin
> registrar wrappers that adapt the `claia.core` plugin classes (which
> would then only depend on the `Base*` ABCs in `claia.core`). This is
> deferred — see "Open Questions / Future Work".

Third parties implement the ABCs and register via entry points. They
never need to know pluggy exists once we resolve the caveat above.

### ParamSpec Replaces `required_args`

Structured parameter declarations replace the loose `List[str]` used
today.

```python
class ParamScope(Enum):
    INIT = "init"        # Passed at plugin construction (credentials, config)
    RUNTIME = "runtime"  # Passed per call (generation params)

class SettingCategory(Enum):
    API = "API Credentials"
    ENDPOINT = "Endpoints & URLs"
    DIRECTORY = "Directories"
    MODEL = "Model Settings"
    PROMPT = "Prompt Settings"
    AGENT = "Agent Settings"
    VLLM = "VLLM Settings"
    APPLICATION = "Application Settings"
    INTEGRATION = "Integration Settings"
    EXTENSION = "Extension Settings"
    GENERATION = "Generation Parameters"
    MISC = "Other"

@dataclass
class ParamSpec:
    name: str
    type: type = str
    scope: ParamScope = ParamScope.RUNTIME
    required: bool = False
    default: Any = None
    description: str = ""
    choices: Optional[List[Any]] = None       # Order matters; used for CLI
    secret: bool = False                      # Mask in logs / :get output
    externally_settable: bool = True          # False = code-only, hidden from CLI/env/JSON
    category: Optional[SettingCategory] = None  # Groups --help output

@dataclass
class ExtensionInfo:
    name: str
    title: str
    description: str
    params: List[ParamSpec] = field(default_factory=list)
```

**What this unlocks:**

- Settings auto-generates CLI flags, env vars, and validation from the
schema. There is no parallel `CONFIG_VARS` tuple list; the only
app-level declarations live as a `List[ParamSpec]` in
`claia.cli.params.APP_PARAMS`, and everything else is discovered
from plugins.
- Clean init vs. runtime separation — `Manager.filter_init_kwargs` and
`Manager.filter_runtime_kwargs` slice a single `combined_kwargs`
dict by scope before dispatch.
- Lenient coerce/validate at the boundary: values are coerced to
`spec.type`, validated against `spec.choices`, and dropped (with a
warning) on failure so the plugin's own default applies.
- Third-party plugins are self-documenting; `claia inspect <plugin>`
is a natural feature, and slate exposes the same metadata over
`GET /api/v1/{agents,architectures,deployments,solvers}`.
- Secret handling is explicit — `secret=True` is masked in logs
(`Manager._mask_for_log`) and in the CLI's `:get` output.
- `externally_settable=False` keeps code-only knobs (defaults wired by
plugins themselves) out of the user-facing surface.

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

Existing text-only definitions default to `TEXT` → `TEXT`. New
modalities are purely additive.

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

Iterate entry points, import each module, read the class's `info`
attribute, record a `PluginEntry` with the class reference but no
instance.

**Phase 2: Instantiation (on first use)**

When a plugin is first needed, instantiate it with filtered kwargs from
Settings (only the `INIT`-scoped params it declared). Cache the
instance.

This requires a convention: **plugins must not do expensive work at
import or class-definition time**. Class-level
`info = ArchitectureInfo(...)` is fine; expensive setup happens in
`__init__`.

### Security: Explicit Param Declaration

Plugins can only receive kwargs they've declared via ParamSpec. A
plugin that wants credentials must declare them in its `info.params`
list, making any attempt to harvest secrets visible in the plugin's
metadata. Additional measures:

- Secret parameters are logged at INFO level during plugin discovery.
Installing a new plugin that requests secrets produces visible
startup output.
- `claia inspect <plugin>` (future) shows the full param list for
audit.

## Migration Roadmap

The work is organized into phases that can be executed sequentially.
Each phase produces a working system — you can pause after any phase.

### Phase 1: Package Restructure (mostly mechanical) — **DONE**

What landed:

- `src/claia_core/` → `src/claia/core/` (PEP 420 namespace contribution).
- `src/claia/` (the old framework) → `src/claia/framework/`.
- `src/claia_cli/` → `src/claia/cli/`.
- No top-level `claia/__init__.py` — `claia` is a namespace package.
- ABCs declared in `claia.core` for each plugin type
(`BaseArchitecture`, `BaseDeployment`, `BaseSolver`,
`BaseDefinitionProvider`, `BasePattern`, `BaseProtocol`,
`BaseToolModule`, `BaseModel`).
- Plugin metadata dataclasses moved to `claia.core.plugins.base`.
- Hookspecs in `claia.framework.hooks` slimmed down to just the
pluggy-marked classes; they import their `*Info` dataclasses from
`claia.core.plugins.base`.
- `claia.framework.__init__.py` is the convenience hub re-exporting
the most commonly used types from `claia.core` and the framework
primitives.
- Single `pyproject.toml` with per-layer extras for documentation and
the future split. Console script repointed to
`claia.cli.__main__:main`. All entry points updated to the new
module paths; group names unchanged.
- Tests reorganised under `src/tests/{core,framework,cli}` mirroring
the package structure. 27/27 pass.
- Slate's imports migrated from the legacy library namespace to `claia.core.*` and
`claia.framework.*`.
- Dropped the unused `aia` dependency.

Known debt carried into later phases:

- Built-in plugin classes still import `pluggy.HookimplMarker`
directly (Phase 5 cleanup, see also Pluggy Stays in `claia.framework`
caveat above).
- External plugins outside the monorepo (e.g., `claia_bob`) may still
reference legacy import paths. Either we ship a small
compatibility shim, update them in lockstep, or document the
breaking change.

### Phase 2: Conversation Observer + slate Integration — **DONE**

What landed:

- `Conversation` accepts an `on_event` callback in its constructor and
via `observe()`. All mutation methods route through the internal
`_record(event, message)` helper, which appends to `_pending_events`
and invokes `_on_event` with error isolation.
- Event-to-message contract documented in
`claia/core/data/models/conversation/conversation.py` and verified
by `src/tests/core/test_conversation_observer.py` (6 tests).
- Explicit streaming methods on `Conversation`:
`start_streaming_message`, `append_stream_chunk` (silent — does not
fire observers, by design), `end_streaming_message`.
- `pull_events()` retained for pull-based consumers.
- Slate's `services/ai.py` ships:
  - `load_claia_conv_observed()` — load + attach the DB observer.
  - `attach_db_observer()` — attach the observer to a Conversation
  constructed in memory (e.g. brand-new conversations), draining any
  `CONVERSATION_CREATED` event already queued.
  - `flush_streaming_content()` — targeted UPDATE of an in-progress
  message's content between observer events.
  - `_make_db_observer()` — translates every `EventType` into the
  matching `AIEvent` / `AIMessage` / `AIMessageAttachment` /
  `AIConversation` mutation on the session.
- The legacy `sync_to_db()` "diff and write" pass was removed from
slate's services and api layers. Every mutating endpoint
(`create_conversation`, `update_conversation`, `send_message`,
`edit_message`, `retry_message`) drives DB writes through the
observer; only `navigate_branch` writes the head column directly
(no domain event for branch navigation).
- Streaming and non-streaming consolidated behind a single
`POST /v1/ai/conversations/<id>/messages` endpoint. Clients pass
`stream: true` to receive Server-Sent Events; the same flag is
available on `edit_message` (when `regenerate=true`) and
`retry_message`. The separate `/messages/stream` route was
removed.
- The SSE flow described above evolved further into
`slate/services/ai_streams.py`, an in-process `StreamRegistry` that
owns its own background worker thread, supports multiple SSE
subscribers per conversation (multi-tab / late joiners),
cooperative cancellation via `request_cancel`, and snapshots on
reconnect. It composes on top of the Phase 2 building blocks
(`load_claia_conv_observed`, `flush_streaming_content`,
`MESSAGE_STREAM_`* events) without changing them.

### Phase 3: ParamSpec Evolution — **DONE**

What landed:

- `ParamScope`, `ParamSpec`, and `SettingCategory` live in
`claia.core.plugins.base`. `ExtensionInfo` now carries
`params: List[ParamSpec]`; the old `required_args: List[str]` field
is gone with no shim.
- `ConversationSettings` was deleted outright. The `Conversation`
object no longer carries `settings`, does not emit
`SETTINGS_UPDATED` events, and slate's `AIConversation` table
dropped its `settings` JSON column. Generation parameters flow
purely through `ParamSpec(scope=RUNTIME)` on model/architecture
plugins.
- `Manager` is the single source of truth for kwarg handling. On it:
  - `Manager.coerce_value(value, target)` — lenient type coercion
  used everywhere (Settings, filter, CLI, `:set`).
  - `Manager.filter_init_kwargs` / `filter_runtime_kwargs` — spec-
  aware slicing that coerces values, validates `choices`, and
  drops (with a `WARNING`) on failure so plugin defaults apply.
  - `Manager.validate_required_init_kwargs` — separate explicit
  check for missing `required=True` INIT params (called at
  instantiation, not at discovery).
  - `Manager._mask_for_log` — secret-aware rendering so
  `spec.secret=True` values never land in plaintext warnings.
- `Registry.manager` is a read-only `@property`; downstream layers
(`Settings`, CLI commands, slate's API) reach coercion and
parameter introspection via `registry.manager.<method>`.
`Registry` calls the filter helpers as `Manager.filter_init_kwargs(...)`
explicitly — no module-level aliases.
- Architecture plugins declare the full per-architecture param
contract — both `INIT` (credentials, endpoints) and `RUNTIME`
(generation knobs like `temperature`, `max_tokens`) — directly on
`ArchitectureInfo.params`. The shared `COMMON_TEXT_RUNTIME_PARAMS`
list is exported from `claia.core.plugins.base` and spread into each
text architecture's params; per-architecture overrides
(e.g. Gemma3's higher `max_tokens` default) are expressed by
declaring the override `ParamSpec` alongside a filtered spread of
the common list. Models themselves are metadata-free.
- `Manager.resolve_runtime_kwargs(kwargs, params)` is the single
entry point for building a fully-resolved RUNTIME kwarg dict: it
seeds from each spec's declared `default` and overlays the coerced
subset of `kwargs` produced by `filter_runtime_kwargs`.
`Registry._run_stream` invokes it against the architecture's params
so concrete `model.generate` implementations consume kwargs
directly (no local spec list, no `update_settings` helper).
- Built-in plugins migrated: OpenAI, Anthropic, OpenRouter, Cloudflare,
RunPod, Massed Compute, LocalLLM, `transformers_generic`, and
`transformers_gemma3` all declare their API tokens as
`scope=INIT, required=True, secret=True, category=API`.
- `claia.cli.settings.Settings` was rewritten around
`OrderedDict[str, ParamSpec]`. App-level declarations moved to
`claia.cli.params.APP_PARAMS`; the old `CONFIG_VARS` tuple list is
gone, and so is the backward-compatible `config_vars` property.
The CLI `--help` renders directly from `ParamSpec` metadata,
grouped by `SettingCategory`.
- CLI / env / `settings.json` precedence still applies, but all three
sources run through `Manager.coerce_value` and spec-level `choices`
validation. `RUNTIME` params use per-type sentinels
(`""` / `None`) so "unset" reliably means "let the plugin's spec
default apply".
- New `reset` command (`:reset <key>`, `:reset --runtime`) clears
individual settings back to their spec default or wipes all
overridden RUNTIME params.
- Slate exposes the full `ParamSpec` metadata over the REST API via a
shared `_serialize_param_spec` / `_serialize_extension_info` pair.
New endpoints: `GET /api/v1/architectures`,
`/api/v1/deployments`, `/api/v1/solvers` (mirror the existing
`/api/v1/agents`).
- Tests: 27/27 claia tests still pass. Conftest's Registry fixture
now monkeypatches `regmod.Manager` with a thin factory class that
re-exposes the real Manager's static methods, so
`Manager.filter_init_kwargs(...)` in `Registry` resolves under test
without any module-level alias.

Not included in this phase (deferred by choice):

- New unit tests specifically for `ParamSpec` coercion, validation,
and CLI round-trip. The existing suite was kept green; fresh
coverage is a separate task.

### Phase 4: Modality + GenerationChunk — **DONE**

What landed:

- New `claia.core.modality` module with `Modality`, `ChunkKind`,
`GenerationChunk`, `text_chunk`, and `iter_text`. Re-exported from
both `claia.core` and `claia.framework` so the convenience hub
carries the new types.
- `ModelDefinition` gained `input_modalities: List[Modality]` and
`output_modalities: List[Modality]`, both defaulting to
`[Modality.TEXT]`. Defaults preserve the text-in / text-out
behaviour of existing definitions.
- `BaseDeployment.run` and the `claia_deployments` hookspec now return
`Iterator[GenerationChunk]`. Built-in deployments (`api`, `local`,
`remote`, `dummy`) wrap each token yielded by their underlying model
into a `ChunkKind.TEXT` chunk; if a model already yields
`GenerationChunk` items they pass through unchanged, so future
multi-modal models don't need a new deployment class.
- `Registry._run_stream` returns the chunk stream directly.
`Registry.run(streaming=True)` now yields `GenerationChunk`; the
non-streaming path concatenates the TEXT chunks into the `Result`.
A new `Registry.stream_text(...)` convenience flattens TEXT chunks
back to `Iterator[str]` for text-only consumers.
- `SimpleAgent` (framework) and `WriterAgent` (CLI) consume the chunk
stream: TEXT chunks are appended to the streaming message and
emitted via `process.emit("token", ...)` as before; non-text chunks
are forwarded via a new `process.emit("chunk", chunk)` event for
downstream consumers that want the richer stream.
- Slate's `BobAgent` (only external consumer of the streaming
registry API) was updated in lockstep. Other slate callers
(`registry.run(..., streaming=False)`, the namer agent) use the
non-streaming `Result`-returning path and were unaffected.
- Built-in model definitions declare modalities: OpenAI and
Anthropic chat models advertise `[TEXT, IMAGE] → [TEXT]`; Gemma-3
multi-modal variants advertise `[TEXT, IMAGE]` input; Stable
Diffusion declares `[TEXT] → [IMAGE]`. Other text-only definitions
keep the defaults.
- Tests: `src/tests/core/test_modality.py` covers the enums, the
`GenerationChunk` / `text_chunk` / `iter_text` helpers, and the
`ModelDefinition` modality defaults. `src/tests/framework/test_registry.py`
gained coverage for `run(streaming=True)` yielding chunks and the
`stream_text` flattener. Full suite: 36/36 passing.

### Phase 5: Lazy Plugin Loading + Pluggy Decoupling — **DONE**

Two-phase plugin loading is now the Manager's default path and
`claia.core` plugins no longer depend on `pluggy`.

- **ABCs expose class-level metadata.** `BaseArchitecture`,
`BaseDeployment`, `BaseSolver`, `BasePattern`, `BaseProtocol`, and
`BaseToolModule` each declare `info: ClassVar[<Info>]` and ship a
default `get_*_info()` that returns `type(self).info`. Plugin authors
override the class attribute; the method hook remains the public
contract exposed to the framework.
- **`PluginEntry` is the canonical discovery record.** The dataclass
carries the entry point, loaded class, discovered `info`, flattened
`ParamSpec` list, the lazy `instance`, and the registrar wrapper
actually handed to pluggy.
- **Discovery reads class attributes, not instances.**
`Manager.discover_plugins()` walks every entry-point group listed in
`PLUGIN_GROUPS` and calls `_populate_entry_metadata()`, which reads
the class-level `info` attribute directly — no plugin is
instantiated during discovery. Architecture plugins declare their
full param contract (both INIT and RUNTIME specs) on
`ArchitectureInfo.params`, so there is no model-class fold-in step;
the plugin itself is the single source of truth for every spec
Settings/CLI/dispatch consumes.
- **Registrar wrappers live in `claia.framework.registrars`.** One
registrar per hook namespace (`ArchitectureRegistrar`,
`DeploymentRegistrar`, `SolverRegistrar`, `DefinitionRegistrar`,
`PatternRegistrar`, `ProtocolRegistrar`, `ToolModuleRegistrar`,
`AgentRegistrar`) wraps a pure plugin instance and carries the
`@hookimpl` markers. `_BaseRegistrar.__getattr__` transparently
proxies unknown attributes to the wrapped plugin so code that used
to reach into the raw instance (`plugin.get_module_tools()`) still
works against the wrapper.
- **Every plugin goes through a registrar.** `_load_plugins` fetches
the registrar class for the group, instantiates the plugin with the
kwargs its specs allow, wraps it, and hands the wrapper to
`pm.register`. No alternate "already uses `@hookimpl`" path exists —
pluggy is fully encapsulated inside the framework.
- **Core plugins are pluggy-free.** All five architectures
(`openai`, `anthropic`, `transformers_generic`, `transformers_gemma3`,
`dummy`), four deployments (`api`, `local`, `remote`, `dummy`), the
default solver, the three definition providers, the default pattern,
the simple protocol, and the `sample`/`system` tool modules now
inherit from their respective ABCs and declare their metadata as
class-level `info` attributes. The `cli` tool module in
`claia.cli.commands.extension` and the `simple` agent in
`claia.framework.agents.simple` follow the same pattern for
consistency.
- **Secret-aware discovery logging.** `Manager._log_discovered_entry`
emits an INFO-level line for every discovered plugin that declares a
secret-scoped `ParamSpec`, surfacing which credentials will be
consumed at startup without leaking values. Non-secret params stay at
DEBUG.
- **Plugins instantiate at load time, not discovery.**
`_load_plugins()` still builds instances when `load_all_plugins()` is
called — that's the natural point where the kwarg environment is
available — but the intermediate registrar hop means the instance is
only materialized once per plugin and only wrapped in a registrar
right before `pm.register()`. Settings-sensitive callers
(`Registry._run_stream`, settings bootstrap) keep using
`get_extension_params()`, which needs only discovery and never forces
full instantiation.

### Phase 6: Demos Folder

After the architectural phases are stable, create `src/demos/` with
concrete scenarios that exercise each layer:

- `demos/core_agent/` — an agent built directly on `claia.core` data
structures with no framework.
- `demos/framework_agent/` — an agent registered as a `claia.framework`
plugin going through `Process`/`Registry`.
- `demos/cli_extension/` — a `claia.cli` extension adding a custom
command.
- Equivalents for other extension points (architecture, deployment,
solver, tool module).

These demos serve as both documentation and continuous validation
that the namespace boundaries hold up under real use.

### Later / Deferred

- Cross-cutting hooks (usage tracking, rate-limit detection, error
classification, caching) — introduce when two or more concrete use
cases exist.
- Wrapper plugins (middleware pattern) — introduce when a third-party
wants to ship one.
- Plugin identifier namespacing (reverse-DNS or similar) — revisit when
third-party plugin ecosystem grows.
- Pydantic-based plugin config schemas — consider if ParamSpec grows
unwieldy or if richer validation is needed.
- Webapp and worker packages — out of scope for this plan.

## Testing Strategy

- Tests live under `src/tests/{core,framework,cli}` mirroring the
package structure.
- `claia.core` tests are pure — no pluggy, no plugin loading, no
framework.
- `claia.framework` tests exercise real pluggy discovery, the
Registry, Process flow.
- `claia.cli` tests exercise command routing, JsonStore, CLI-specific
agents.
- Shared fixtures (common conversation shapes, dummy models) live in
`src/tests/conftest.py` or are duplicated between suites if small.
Don't over-engineer this.

## Documentation Approach

- Each subpackage ships a `README.md` with focused scope and examples
(live alongside the code in `src/claia/{core,framework,cli}/`).
- `claia.core` README: library usage, data models, how to implement
plugins.
- `claia.framework` README: framework usage, Registry, Process, agents.
Highlights the convenience hub re-exports.
- `claia.cli` README: end-user CLI guide.
- The observer contract (event → message mapping) is documented in
`claia/core/data/models/conversation/conversation.py` docstrings.
- ParamSpec patterns for secret handling and audit are documented
alongside the plugin system docs.

## Decisions Log


| Decision                    | Chosen                                                                                  | Rationale                                                                               |
| --------------------------- | --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Architecture style          | Library + framework + CLI split (three subpackages)                                     | Preserves flexibility of a library while keeping opinionated framework convenience      |
| Package boundary            | PEP 420 namespace `claia` with subpackages `claia.core`, `claia.framework`, `claia.cli` | Hierarchical imports today, independently distributable tomorrow, no runtime hacks      |
| Convenience hub location    | `claia.framework.__init__.py` (re-exports from `claia.core`)                            | Namespace package can't have top-level `__init__.py`; framework is the natural umbrella |
| Repo layout                 | Monorepo with single `pyproject.toml` during dev, splittable later                      | Simpler until external users diverge; per-layer extras document the boundary            |
| Conversation structure      | List of messages with `parent_id`, tree implicit                                        | Simple, existing, no new abstractions                                                   |
| Mutation notifications      | Observer (`on_event` callback)                                                          | Real-time, push-based, standard pattern                                                 |
| Multi-observer support      | Single observer for now                                                                 | Simpler; add later if needed                                                            |
| Per-chunk observer fire     | No — `append_stream_chunk` silent                                                       | Avoids event flooding                                                                   |
| Streaming persistence       | Batched synchronous flush (Option 1)                                                    | Best tradeoff for current scale                                                         |
| Content flush mechanism     | Targeted function, not observer                                                         | Keeps observer API clean; explicit control                                              |
| `pull_events()` fate        | Kept as alternative                                                                     | Non-breaking, useful for pull-based consumers                                           |
| Pluggy location             | Framework only                                                                          | Library stays dependency-light                                                          |
| Plugin contracts            | ABCs in `claia.core`, hookspecs in `claia.framework`                                    | Two different concerns, both explicit                                                   |
| Plugin metadata dataclasses | Live in `claia.core.plugins.base`                                                       | Plugin implementations can construct them without depending on the framework            |
| Plugin metadata schema      | Custom `ParamSpec` (not Pydantic)                                                       | Avoids core dependency; can upgrade later                                               |
| Runtime param delivery      | `ParamSpec(scope=RUNTIME)` forwarded via `registry.run(**kwargs)`                       | Replaces `ConversationSettings`; keeps the `Conversation` object purely a data carrier  |
| Param validation posture    | Lenient coerce + drop-on-failure with WARNING                                           | Plugin defaults are the safety net; strict rejection was heavier than needed            |
| Kwarg-handling ownership    | `Manager` owns coercion and filtering; `Settings` reuses it via `registry.manager`      | One source of truth; no duplicated helpers or module-level aliases                      |
| Settings schema             | Single `ParamSpec` list; no parallel `CONFIG_VARS` tuples                               | Deleted the shim once the CLI `--help` was updated to render from `ParamSpec` directly  |
| Plugin identifiers          | Friendly names only for now                                                             | Deferred reverse-DNS/namespacing discussion                                             |
| Entry-point group names     | Stable `claia.*` strings (unchanged across migration)                                   | They are labels, not module paths; preserves external plugin compatibility              |
| Plugin loading              | Two-phase (metadata eager, instance lazy)                                               | Startup performance + plays well with ParamSpec                                         |
| Plugin security             | Explicit ParamSpec declarations                                                         | Principle of least privilege                                                            |
| Output type                 | `GenerationChunk` stream                                                                | Unifies text/image/audio/video                                                          |
| Backward compatibility      | Coordinate updates, no shims                                                            | Internal project; slate is the only first-party consumer                                |
| CLI `WriterAgent`           | Stays programmatically registered in `claia.cli`                                        | CLI-specific, not distributable                                                         |
| `aia` dependency            | Removed                                                                                 | Unused since early refactor                                                             |


## Open Questions / Future Work

- `**claia.core` pluggy decoupling** — built-in plugin classes still
import `pluggy.HookimplMarker`. Resolve by providing thin registrar
wrappers in `claia.framework` (Phase 5).
- **External plugin compatibility** — packages that import from legacy
CLAIA paths need either a shim or a coordinated update.
Pick a strategy when the first non-monorepo plugin runs into it.
- **Plugin identifier namespacing** — deferred; likely reverse-DNS or
similar when the plugin ecosystem grows.
- **Multiple observer support** — add if a concrete use case appears
(e.g., websocket broadcast alongside DB persistence).
- **Stream resumption after crash** — the current design bounds data
loss but does not resume interrupted streams. If resumption becomes
a requirement, consider a write-ahead chunk table or durable
message queue.
- **Cost/usage tracking** — will likely become a cross-cutting pluggy
hook once multiple providers need it.
- **Webapp worker package** — scoped for a future iteration.

