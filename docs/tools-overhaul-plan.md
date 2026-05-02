# Tools Subsystem Overhaul Plan

This document describes a planned restructure of the `claia.core.tools`
subsystem and the closely-related streaming/parsing path. It covers the
introduction of a streaming **parser** module in `claia.core`, the
removal of the **pattern** plugin axis, the rewrite of the **protocol**
plugin contract so protocols own tool discovery, the relocation of
native tool-module plumbing into the simple protocol, and the future
addition of an **MCP protocol** that exposes external Model Context
Protocol servers as tools.

The intent is a structure we can live with for years. Everything below
was decided with that horizon in mind, and alternatives we considered
and rejected are documented inline so future work has the rationale.

> **Implementation notes:** the running log of as-built changes lives
> in [`tools-overhaul-implementation-notes.md`](./tools-overhaul-implementation-notes.md).
> That file records the concrete files added, modified, and removed
> in each phase, along with any deviations from this plan and any
> follow-up items discovered along the way. Update it as work
> progresses; this plan document stays focused on intent and design.

---

## 1. Why we're changing things

The current tool subsystem under `claia.core.tools/` has three plugin
axes (patterns, protocols, modules) plus a flat command catalog owned by
`Registry`. It assumes:

- The model emits text containing tool calls in a known tag format.
- That text is parsed locally by a "pattern" plugin.
- A "protocol" plugin dispatches the parsed match against a global
  catalog of Python callables aggregated from "tool module" plugins.

This holds up cleanly for built-in tools but strains in three directions
we now care about:

1. **MCP support.** MCP is a wire protocol for tool execution. Wrapping
   each MCP server as a `BaseToolModule` either forces a per-server
   Python wrapper (defeats the ecosystem reuse that motivates MCP) or
   needs the same module class instantiated N times from runtime
   config (fights the entry-point discovery model). The natural home
   for MCP is a single protocol plugin that reads a server-list config
   and speaks the wire. That, however, requires protocols to *own*
   tool discovery rather than merely consume a global catalog.
2. **Native function-calling APIs.** Modern providers (OpenAI,
   Anthropic, etc.) deliver tool calls as structured fields on the
   assistant message, not as text spans. The current
   `process_content(content: str) -> str` signature cannot carry them,
   and the "pattern" abstraction is irrelevant for that source of
   tool calls.
3. **Streaming, multi-tag content.** We want unified handling for
   `<tool>...</tool>`, `<thinking>...</thinking>`,
   `<reference guid="…">…</reference>`, etc., emitted as part of a
   streaming assistant response. The existing pattern ABC is built
   around "find spans in a complete string" and has no streaming
   model.

The overhaul addresses all three.

---

## 2. Decisions and their rationale

These are settled design decisions for the overhaul. The rationale is
preserved so future maintainers don't need to re-litigate them.

### 2.1 Protocols own tool discovery

The single biggest change. Today `Registry` owns the commands catalog
and `BaseProtocol.execute(...)` receives it as an argument. After the
overhaul, each protocol exposes its own tool inventory via
`get_tool_references()`, and the registry asks every loaded protocol
for its inventory and assembles a unified index.

- **Why**: MCP needs to surface tools that don't exist as Python
  callables anywhere in this codebase. They live behind sessions the
  MCP protocol owns. There is no clean way to feed those into a global
  catalog without inverting the data flow. With protocols owning their
  inventory, native tools, MCP tools, and any future protocol all use
  the same shape.
- **Alternative considered**: Keep the global catalog and have an MCP
  module-per-server. Rejected because it forces ecosystem-MCP-server
  reuse to live behind hand-written Python wrappers, which is the
  opposite of what MCP is for.

### 2.2 The simple protocol becomes the bridge for native tool modules

`BaseToolModule` and `claia.tool_modules` entry points stay. They remain
the way native, code-defined tool groups are shipped. The simple
protocol is rewritten to *consume* loaded tool modules at construction
and expose them through the new protocol contract.

- **Why**: We don't want to push every tool author into knowing what a
  protocol is. A third-party shipping a Python tool module continues
  to ship a `BaseToolModule` and register it under
  `claia.tool_modules`. The simple protocol is the universal consumer
  of those.
- **Side effect**: The kwargs-prep + JSON arg decoding logic currently
  in `Registry._prepare_command_kwargs` and the flat catalog walking
  in `SimpleProtocolPlugin.execute` move into the simple protocol's
  internals. The registry stops knowing what an `ArgumentDefinition`
  is.

### 2.3 The pattern axis dissolves into a parser module + model defs

The pattern plugin axis is removed. Its responsibilities split:

- The **token strings** for each tag type move onto the per-model
  definition as an optional `tag_overrides` field. There is **one
  default per tag type** registered globally; a model definition only
  carries an override when it deviates from the default.
- The **actual extraction** moves into a new
  `claia.core.parsers` package. It is a streaming, stateful parser
  with a generic tag-extraction model — not tool-specific.

- **Why split**: Token strings are a property of the model
  (different models train on different formats); extraction is a
  generic streaming-text concern reusable for thinking, references,
  and future tag types. Coupling them as one plugin per
  parser-format hurt both axes.
- **Why one default per tag type**: simplicity. Authors who want a
  custom format set it on their model def; everyone else gets the
  default. This avoids a registry of patterns competing for the same
  tag.

### 2.4 Messages get utility siblings, not children

When the parser identifies a tagged span inside an assistant message
text, the consumer (the agent) creates a sibling **utility-role**
message that references the source assistant message by id and carries
the start/end indices into the source text.

- **Why siblings, not children**: keeps `Conversation` flat and
  preserves the existing linear-list mental model. No changes to
  iteration, persistence, or replay shapes.
- **Why not splice tool results back into the source text**: the
  current `process_content` rewrites the assistant's text with tool
  output. That produces text the model never emitted and means the
  model's next turn sees its own previous output mutated. Siblings
  preserve the assistant's actual output verbatim and treat parsed
  artifacts as first-class derived data.
- **Indexes are stable**: because the assistant message text is never
  rewritten after streaming completes, the start/end indices stored
  on a utility message remain valid for the lifetime of the
  conversation.

### 2.5 Tag type stays on the message — for dispatch, not rendering

Utility messages carry a `tag_type` field. Its purpose is **categorical
dispatch**: the agent uses it to decide whether to forward the message
to the tool protocol, log it as thinking, resolve it as a reference,
etc. It is *not* needed for positional rendering, which depends only on
indices.

- Different models will use different open/close strings for the same
  category (e.g., `<tool_call>` vs `[TOOL_CALL]` for `TOOL`); the
  categorical type is the stable handle, the strings are not.

### 2.6 Optional XML-style attribute parsing on tags

Tags optionally carry attributes. Two forms are supported:

- `<reference guid="something">...</reference>` — XML-like.
- `[TOOL_CALL NAME='TOOL_NAME']content[/TOOL_CALL]` — bracket-tagged
  with attributes.

The parser extracts `key=value` pairs (single-quoted, double-quoted, or
unquoted-no-whitespace values) into a `Dict[str, str]` on the resulting
tag event. Whether a given tag spec parses attributes is opt-in via the
spec.

### 2.7 Strict LIFO nesting

The parser maintains a stack of open tags. A close token must match the
top of the stack. Mismatched closes produce an error event; an
end-of-stream with a non-empty stack is also an error. There is no
recovery heuristic; the streaming layer decides how to handle errors
(typically log + drop the affected utility, continue parsing).

### 2.8 First-in-list wins on duplicate tool names

When the registry assembles the unified tool index by iterating
protocols and their `get_tool_references()` outputs, duplicate qualified
names are skipped (first one registered wins). A debug-level log notes
the skip. Order is determined by pluggy's load order; we do not add an
explicit `priority` field in the first cut.

### 2.9 Namespacing of qualified names

- Native tools keep the existing `module.tool` form
  (e.g., `system.clear`).
- Protocol-sourced tools beyond simple are prefixed with the protocol
  name and any sub-namespace they need
  (e.g., `mcp.<server_name>.<tool_name>`).
- The registry's index keys are these qualified names. Resolution from
  unqualified names emitted by the model is the parser-consumer's
  problem (the agent / tool protocol decides whether to accept a
  short-form name and how to disambiguate).

### 2.10 ArgumentDefinition stays for native tools

`ArgumentDefinition` is kept as the native module's argument schema. It
moves "down" into the simple protocol — the registry no longer knows
about it. JSON Schema fidelity for MCP tools is handled inside the MCP
protocol; conversion between JSON Schema and `ArgumentDefinition` is
**not** attempted in the first cut. Each protocol describes its tools'
arguments in whatever shape suits it; `ToolReference` carries a
protocol-agnostic surface (described below).

---

## 3. The parser subsystem

New package: `claia/core/parsers/`.

### 3.1 Package layout

```
claia/core/parsers/
  __init__.py
  types.py        # TagType, TagSpec, TextEvent, TagEvent, ParseEvent
  defaults.py     # DEFAULT_TAGS registry
  streaming.py    # StreamingTagParser
  attributes.py   # Attribute parser (small state machine)
  resolution.py   # resolve_tag_specs(model_def) -> List[TagSpec]
  README.md
```

### 3.2 Types

```python
class TagType(Enum):
  TOOL = "tool"
  THINKING = "thinking"
  REFERENCE = "reference"
  # extensible

@dataclass(frozen=True)
class TagSpec:
  tag_type: TagType
  open_token: str                              # full open OR open prefix
  close_token: str
  attribute_terminator: Optional[str] = None   # set => parse attrs

@dataclass
class TextEvent:
  text: str
  start_index: int   # absolute position in the stream
  end_index: int     # exclusive

@dataclass
class TagEvent:
  tag_type: TagType
  content: str               # raw content between open and close tokens
  attributes: Dict[str, str] # parsed attrs; empty when not enabled
  start_index: int           # absolute position of the open token's first char
  end_index: int             # exclusive; position just past the close token
  raw_open: str              # the matched open token text including attrs
  raw_close: str             # the matched close token text

ParseEvent = Union[TextEvent, TagEvent]
```

### 3.3 Default tag specs

`defaults.py` registers exactly one `TagSpec` per `TagType`. Suggested
starting set (subject to revision when implemented):

- `TagType.TOOL` — `open_token="[TOOL_CALL]"`, `close_token="[/TOOL_CALL]"`,
  no attribute terminator. (The tool protocol can specify a separate
  attribute-bearing default if we decide to.)
- `TagType.THINKING` — `open_token="<think>"`, `close_token="</think>"`.
- `TagType.REFERENCE` — `open_token="[REF]"`, `close_token="[/REF]"`.

Per-model overrides supersede these per-tag-type. There is never more
than one spec of a given `TagType` active in a given parser instance.

### 3.4 TagSpec interpretation

| `attribute_terminator` | `open_token` semantics                                            | Example                                |
| ---------------------- | ----------------------------------------------------------------- | -------------------------------------- |
| `None`                 | Full opening literal; matched verbatim.                           | `[TOOL_CALL]`, `<think>`               |
| set (e.g. `]`, `>`)    | Opening **prefix**; whitespace + `key=value` pairs are tolerated  | `[TOOL_CALL` … `]`, `<reference` … `>` |
|                        | between the prefix and the terminator.                            |                                        |

Attribute syntax inside the region:
- whitespace-separated `key=value` pairs
- `value` may be `"…"`, `'…'`, or unquoted (no whitespace, terminator
  ends it)
- keys are alphanumeric + underscore + dot (XML-like leniency)

### 3.5 Streaming behavior

`StreamingTagParser`:

```python
class StreamingTagParser:
  def __init__(self, tag_specs: List[TagSpec]) -> None: ...
  def feed(self, chunk: str) -> Iterator[ParseEvent]: ...
  def flush(self) -> Iterator[ParseEvent]: ...   # call at end-of-stream
```

Internal state:

- `_buffer: str` — accumulated unconsumed input.
- `_cursor: int` — absolute index into the conceptual stream so events
  can carry stable positions. Equal to total length consumed so far.
- `_stack: List[OpenTag]` — open tags awaiting their close token in
  LIFO order. Each `OpenTag` carries `tag_type`, `attributes`,
  `open_start_index`, `content_start_index`, `raw_open`.

`feed()` semantics:

1. Append the chunk to `_buffer`.
2. Walk forward emitting events:
   - When the stack is empty and a position cannot be the start of any
     spec's `open_token`, that character is consumed into a pending
     `TextEvent` body.
   - When an `open_token` (or open prefix + attrs + terminator)
     completes, emit any pending `TextEvent`, push an `OpenTag` onto
     the stack, mark the content start position.
   - When the stack is non-empty: continue scanning for either a
     nested `open_token` of any spec or the `close_token` of the
     stack top. New nested opens push the stack; matching closes pop
     the stack and emit a `TagEvent` whose `content` is the buffered
     text between the popped open's content-start and the close
     token's start.
   - On a close token that doesn't match the top of the stack, emit
     an error event (TBD type — see §11) and continue with the
     mismatched close consumed as plain text.
3. If a partial match is in progress at the end of the chunk (open
   token prefix, in-flight attribute region, or close-token prefix),
   leave it in `_buffer` and stop. Do not emit a `TextEvent` for
   characters that might still become part of a tag.

`flush()` is called by the consumer after the model has finished
streaming. It emits any pending `TextEvent` and, if the stack is
non-empty, an end-of-stream error event listing unclosed tags.

### 3.6 Realtime emission

The parser is a generator-style yielder, not a callback-based observer.
Consumers (the agent loop, today) drive it explicitly:

```python
parser = StreamingTagParser(resolve_tag_specs(model_def))
for chunk in stream:
  for ev in parser.feed(chunk):
    handle(ev)
for ev in parser.flush():
  handle(ev)
```

Where `handle(ev)` for the agent loop:

- `TextEvent` → append to the assistant message text.
- `TagEvent` → create a utility-role sibling message; if
  `tag_type == TOOL`, hand the message to the registry for tool
  execution.

### 3.7 Notes and edge cases

- Two specs whose open tokens prefix-match each other (e.g.,
  `[TOOL_CALL]` and `[TOOL_CALL`) cannot both be active at once. Since
  we have one default per tag type and overrides only swap, this is
  not encountered in practice; documented as a constraint.
- The parser does **not** attempt to interpret tag content
  (no JSON parsing, no XML parsing of inner content). Content is
  delivered verbatim. Tag-type-specific decoding belongs to the
  consumer (e.g., the simple protocol JSON-decodes tool call content
  into `name` + `parameters`).
- Per-model override merges are **per-tag-type replacement**, not
  field-level merging. If a model overrides `TagType.TOOL`, it
  provides a complete `TagSpec`.

---

## 4. Message and Conversation changes

### 4.1 New role and fields

`Role` enum gains:

```python
Role.UTILITY = "utility"
```

`Message` gains the following optional fields (relevant only when
`role == UTILITY` unless noted):

| Field               | Type                      | Notes                                                                                 |
| ------------------- | ------------------------- | ------------------------------------------------------------------------------------- |
| `tag_type`          | `Optional[TagType]`       | Categorical type for dispatch (TOOL / THINKING / REFERENCE / …).                      |
| `source_message_id` | `Optional[str]`           | The id of the assistant message this utility was parsed from.                         |
| `start_index`       | `Optional[int]`           | Absolute character offset of the tag's open token in the source message text.         |
| `end_index`         | `Optional[int]`           | Exclusive end offset just past the close token.                                       |
| `attributes`        | `Optional[Dict[str, str]]`| Parsed XML-style attributes from the open token, when present.                        |

Existing fields (id, role, content, timestamps, etc.) are unchanged.
Utility messages' `content` carries the raw text between the open and
close tokens — same as `TagEvent.content`.

### 4.2 Conversation iteration

Utility messages are stored inline in the conversation list, but most
consumers do not want them sent back to the model. The conversation
linearization helper used by agents/architectures should filter
`role == UTILITY` by default, with a flag to include them when needed
(e.g., for re-rendering UI, debugging, or replay).

### 4.3 Persistence

Persisters (claia.core.data persistence layer) need to handle the new
role and the new fields. Backwards compatibility for existing
conversations: missing fields default to `None`; `Role.UTILITY` is a
new value, old data won't have it. No migration needed.

---

## 5. Model definition changes

`ModelDefinition` gains:

```python
tag_overrides: Optional[Dict[TagType, TagSpec]] = None
```

When set, entries replace the global default for the specified
`TagType` for parsers built against this model definition. Resolution
helper:

```python
def resolve_tag_specs(model_def: ModelDefinition) -> List[TagSpec]:
  out = dict(DEFAULT_TAGS)
  if model_def.tag_overrides:
    out.update(model_def.tag_overrides)
  return list(out.values())
```

Tokenizer-aware token resolution is **deferred**. We assume hand-coded
token strings on each definition. A future enhancement could derive the
correct token strings from the model's tokenizer (special-token vs
text-token forms), but that's out of scope for this overhaul.

---

## 6. Protocol subsystem rewrite

### 6.1 New `ToolReference`

A protocol-agnostic descriptor that the registry stores. Lives in
`claia.core.tools.types` (new module) or alongside the existing
`claia.core.plugins.base` dataclasses — TBD during implementation.

```python
@dataclass
class ToolReference:
  qualified_name: str               # e.g., "system.clear" or "mcp.fs.read_file"
  description: str
  protocol_name: str                # which protocol owns and runs this tool
  parameter_schema: Any             # opaque to the registry; protocol-specific
                                    # (e.g., Dict[str, ArgumentDefinition] for simple,
                                    #  raw JSON Schema for mcp)
  tags: List[str] = field(default_factory=list)   # optional metadata for UI/filters
```

The `parameter_schema` field is intentionally typed `Any`. The registry
does not introspect or validate it. UIs and the agent that need to
render argument forms read this in a protocol-aware way (a renderer
asks the protocol "give me a form for this tool"). The registry's job
is identification and dispatch.

### 6.2 New `BaseProtocol`

```python
class BaseProtocol(ABC):
  info: ClassVar[ProtocolInfo]

  def get_protocol_info(self) -> ProtocolInfo:
    return type(self).info

  def start(self) -> None:
    """Open sessions, validate config. Default: no-op."""

  def stop(self) -> None:
    """Close sessions. Default: no-op."""

  def refresh(self) -> None:
    """Re-fetch dynamic tool inventories. Default: no-op."""

  @abstractmethod
  def get_tool_references(self) -> List[ToolReference]:
    """Tools this protocol owns and can execute."""

  @abstractmethod
  def execute(
    self,
    qualified_name: str,
    raw_payload: str,
    conversation,
    **kwargs,
  ) -> Result:
    """Execute the named tool.

    The protocol receives the raw content string from the parser
    (the body between open/close tags) and is responsible for
    decoding it into call parameters in whatever format that protocol
    uses (JSON for simple, etc.). Cross-cutting kwargs (settings,
    cancellation tokens, tool_context bits) come through **kwargs.
    """
```

Notes:

- `execute()` no longer receives a `commands` catalog argument. The
  protocol owns its inventory.
- `execute()` receives the **raw content** from the parser, not a
  pre-decoded `parameters: Dict[str, Any]`. JSON decoding (for the
  simple protocol) or whatever decoding MCP wants is internal to the
  protocol. Rationale: the parser is generic and tag-agnostic; tag
  payload semantics (JSON vs MCP envelope vs custom) belong to the
  protocol.
- `start()` / `stop()` are called by the framework on plugin
  load/unload. `refresh()` is called by callers that need to react to
  inventory changes (e.g., MCP `notifications/tools/list_changed`).

### 6.3 Hookspec, registrar, entry points

The pluggy hookspec (`claia.framework.hooks.protocol`) is updated to
mirror the new ABC:

```python
class ProtocolHooks:
  @hookspec
  def get_protocol_info(self) -> ProtocolInfo: ...
  @hookspec
  def start(self) -> None: ...
  @hookspec
  def stop(self) -> None: ...
  @hookspec
  def refresh(self) -> None: ...
  @hookspec
  def get_tool_references(self) -> List[ToolReference]: ...
  @hookspec
  def execute(self, qualified_name, raw_payload, conversation, **kwargs) -> Result: ...
```

`ProtocolRegistrar` in `claia.framework.registrars` is updated in
parallel. The `claia.tool_protocols` entry point group is unchanged in
name.

The `claia.tool_patterns` entry point group is **removed**. The
corresponding hookspec module and registrar are deleted.

---

## 7. Registry changes

### 7.1 Tool index

`Registry` replaces the current `_commands_catalog: Dict[str, Dict]`
with:

```python
_tool_index: Dict[str, ToolReference]   # qualified_name -> reference
_protocols: Dict[str, BaseProtocol]     # protocol_name -> instance
```

Index assembly (called after protocols load and at every `refresh()`):

```python
def _rebuild_tool_index(self) -> None:
  index: Dict[str, ToolReference] = {}
  for protocol in self._iter_protocols():           # pluggy load order
    for ref in protocol.get_tool_references():
      if ref.qualified_name in index:
        logger.debug(
          "Skipping duplicate tool %s from protocol %s; first registration wins",
          ref.qualified_name, ref.protocol_name,
        )
        continue
      index[ref.qualified_name] = ref
  self._tool_index = index
```

### 7.2 New public API

```python
def list_tools(self) -> List[ToolReference]: ...
def get_tool(self, qualified_name: str) -> Optional[ToolReference]: ...
def execute_tool(
  self,
  qualified_name: str,
  raw_payload: str,
  conversation,
  **kwargs,
) -> Result:
  ref = self._tool_index.get(qualified_name)
  if ref is None:
    return Result.fail(f"Tool not found: {qualified_name}")
  protocol = self._protocols.get(ref.protocol_name)
  if protocol is None:
    return Result.fail(
      f"Protocol '{ref.protocol_name}' for tool '{qualified_name}' not loaded"
    )
  return protocol.execute(qualified_name, raw_payload, conversation, **kwargs)
```

### 7.3 Removal of `process_content`

`Registry.process_content` is removed. The agent layer drives the
parser directly and calls `Registry.execute_tool` for `TOOL`-typed tag
events. See §9.

A transitional thin shim of the old `process_content` may be retained
for one phase to keep non-agent callers compiling; it is deleted by
the end of phase 5.

### 7.4 `_prepare_command_kwargs` moves

The kwargs prep helper (currently in `Registry`) moves into the simple
protocol along with the rest of the native-callable plumbing. The
registry stops knowing about `ArgumentDefinition`. CLI direct-execution
paths (`run_command`) either move to call into the simple protocol
explicitly or stay as a registry method that forwards to the simple
protocol for native tools only.

---

## 8. Simple protocol

### 8.1 Layout

```
claia/core/tools/protocols/simple/
  __init__.py
  protocol.py         # SimpleProtocolPlugin (BaseProtocol impl)
  dispatcher.py       # kwargs prep, callable resolution
  payload.py          # raw_payload (JSON) -> (name, parameters) decoder
  README.md
```

### 8.2 Construction and tool discovery

`SimpleProtocolPlugin` is constructed with the loaded native tool
modules at framework startup. `get_tool_references()` aggregates
`module.get_module_tools()` across all of them and converts
`ToolDefinition` -> `ToolReference`:

```python
def get_tool_references(self) -> List[ToolReference]:
  refs = []
  for module in self._modules:
    module_info = module.get_module_info()
    for tool_name, tool_def in module.get_module_tools().items():
      refs.append(ToolReference(
        qualified_name=f"{module_info.name}.{tool_name}",
        description=tool_def.description,
        protocol_name="simple",
        parameter_schema=tool_def.arguments,   # Dict[str, ArgumentDefinition]
      ))
  return refs
```

### 8.3 Execute

```python
def execute(self, qualified_name, raw_payload, conversation, **kwargs) -> Result:
  module_part, tool_part = qualified_name.split(".", 1)   # "module.tool"
  tool_def = self._lookup(module_part, tool_part)
  if tool_def is None:
    return Result.fail(f"Tool not found: {qualified_name}")
  parameters = json.loads(raw_payload) if raw_payload.strip() else {}
  prepared = prepare_command_kwargs(parameters, tool_def, extra_kwargs={
    "conversation": conversation,
    **kwargs,
  })
  result = tool_def.callable(**prepared)
  return _normalize_result(result)
```

### 8.4 Result normalization

`_normalize_result` wraps `str` returns in `Result.ok(...)`, passes
`Result` through, fails on anything else. Same behavior as today's
`SimpleProtocolPlugin.execute`, just relocated.

### 8.5 What native tool modules look like

`BaseToolModule` is unchanged. `ToolDefinition` and `ArgumentDefinition`
are unchanged. Existing modules (`sample`, `system`, the CLI command
extension module) need no code changes for this overhaul.

---

## 9. Agent loop migration

The agent that streams an assistant turn is the one that owns the
parser instance for that turn.

Pseudocode:

```python
specs = resolve_tag_specs(model_def)
parser = StreamingTagParser(specs)
assistant_msg = conversation.start_assistant_message()

for chunk in deployment.run(...):
  for ev in parser.feed(chunk.text):
    if isinstance(ev, TextEvent):
      assistant_msg.append_text(ev.text)
    elif isinstance(ev, TagEvent):
      utility = conversation.append_utility(
        source_message_id=assistant_msg.id,
        tag_type=ev.tag_type,
        content=ev.content,
        attributes=ev.attributes,
        start_index=ev.start_index,
        end_index=ev.end_index,
      )
      if ev.tag_type == TagType.TOOL:
        # raw content is, e.g., a JSON object {"name": "...", "parameters": {...}}
        # the agent decides what qualified_name to dispatch to
        name, _ = simple_payload.peek_name(ev.content)  # or similar
        result = registry.execute_tool(name, ev.content, conversation)
        conversation.append_tool_result(
          source_utility_id=utility.id,
          result=result,
        )

for ev in parser.flush():
  ...   # same handling
```

The exact tool-result message shape (own utility tag type, separate
role, etc.) is finalized during phase 7. The data flow above is the
target.

---

## 10. MCP protocol (future)

This section describes the eventual MCP protocol implementation. It is
not part of the first wave of work but is in scope for the design so
the protocol abstraction is sized correctly.

### 10.1 Layout

```
claia/core/tools/protocols/mcp/
  __init__.py
  protocol.py         # MCPProtocolPlugin
  transport.py        # stdio + streamable-HTTP transports
  jsonschema.py       # JSON Schema -> ToolReference parameter_schema passthrough
  config.py           # server-list config schema
  README.md
```

### 10.2 Configuration

MCP servers are declared in a config block (mcp.json-style) consumed
by `MCPProtocolPlugin.__init__` via a single INIT-scoped parameter
(`servers`, type `dict` or `list[dict]`). Each entry:

```jsonc
{
  "name": "fs",
  "transport": "stdio",         // or "streamable-http"
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "/data"],
  "env": { "FOO": "bar" },
  "auth": { ... }               // optional, transport-dependent
}
```

`ParamSpec` may need to accept structured nested specs to model this
cleanly for the CLI; alternatively, MCP reads the raw dict and parses
it internally. Decision deferred to MCP implementation phase.

### 10.3 Lifecycle

- `start()` opens a session per configured server. Failed servers log
  and are skipped (the protocol still loads with partial inventory).
- `get_tool_references()` returns one `ToolReference` per `tools/list`
  entry per session, qualified as `mcp.<server_name>.<tool_name>`. The
  `parameter_schema` field carries the raw JSON Schema from the MCP
  server.
- `execute()` decodes `raw_payload` as JSON parameters, dispatches via
  `session.call_tool(...)`, and flattens the resulting MCP
  `CallToolResult` into a claia `Result`. Lossy: image/embedded-
  resource content is dropped or summarized in the first cut. To be
  revisited if/when richer Result content lands.
- `refresh()` re-runs `tools/list` per session in response to
  `notifications/tools/list_changed`.

### 10.4 Result flattening rules (first cut)

```python
def _flatten(call_result) -> Result:
  if call_result.is_error:
    text = "\n".join(c.text for c in call_result.content if c.type == "text")
    return Result.fail(text or "MCP tool returned error")
  text_parts = [c.text for c in call_result.content if c.type == "text"]
  joined = "\n".join(text_parts)
  return Result.ok(joined)
```

Non-text content (image, embedded resource) is logged at debug level
and omitted. Future Result-content expansion may carry it through
without flattening.

---

## 11. Phase plan

Each phase is independently mergeable. Tests added in the same phase as
the code they cover.

### Phase 1 — Parser core (no dependencies on the rest)

- `claia/core/parsers/` with all of §3 in place.
- Test coverage:
  - simple non-attributed tag spans
  - attributed tags (XML-style and bracket-style)
  - tags split across chunk boundaries (every legal break point)
  - nested tags in strict LIFO order
  - mismatched close tokens
  - non-empty stack at flush
  - attributes with single quotes, double quotes, unquoted values,
    and missing values
  - text events between tags
  - text-only stream (no tags) flushes correctly

### Phase 2 — Tag specs in model definitions

- Add `tag_overrides` field to `ModelDefinition`.
- Add `resolve_tag_specs` helper.
- Update existing model definitions (or leave at default).
- Tests for resolution merging.

### Phase 3 — Message + Conversation extensions

- Add `Role.UTILITY`.
- Add new `Message` fields (`tag_type`, `source_message_id`,
  `start_index`, `end_index`, `attributes`).
- Update `Conversation` linearization to filter utility messages by
  default; expose include flag.
- Update persistence and exporters; round-trip tests.

### Phase 4 — Protocol contract rewrite

- New `ToolReference` dataclass.
- New `BaseProtocol` ABC.
- New hookspec, new registrar.
- Old contracts still importable under deprecation banner.
- Update `Manager` to call `start()` after instantiation and `stop()`
  on teardown; surface `refresh()` from the registry.

### Phase 5 — Simple protocol rewrite

- Move `_prepare_command_kwargs` and JSON decoding from `Registry`
  into the simple protocol.
- Implement the three-file split (`protocol.py`, `dispatcher.py`,
  `payload.py`).
- `Registry` rebuilds the tool index from protocols; old
  `_commands_catalog` removed.
- `Registry.execute_tool`, `list_tools`, `get_tool` added.
- Transitional `process_content` shim retained.
- All existing native-tool tests continue to pass.

### Phase 6 — Agent loop migration

- Agent uses `StreamingTagParser` directly per §9.
- All callsites of `Registry.process_content` migrated.
- Transitional shim deleted at end of phase.
- End-to-end tests covering: streaming text-only response, streaming
  with one tool call, streaming with multiple tool calls,
  streaming with thinking + tool call mixed.

### Phase 7 — Pattern subsystem removal

- Delete `claia/core/tools/patterns/` (base, default,
  `__init__.py`, README).
- Delete `claia/framework/hooks/pattern.py`.
- Delete `PatternRegistrar` and remove from `REGISTRAR_BY_GROUP`.
- Remove `claia.tool_patterns` entry point.
- Remove pattern-related Manager methods
  (`get_pattern_by_name`, `get_default_pattern`, etc.).
- Remove `PatternInfo` dataclass and `ToolCallMatch` (the latter is
  obsoleted by `TagEvent`; if anything else depended on it, those
  callers migrate to `TagEvent`).

### Phase 8 — MCP protocol

- Implement per §10.
- Add documentation, sample config, examples.
- Add to `claia.tool_protocols` entry points.

Phases 1–3 can proceed in parallel after Phase 1 is well underway.
Phases 4–7 are sequential.

---

## 12. Open considerations

These are intentionally deferred or unresolved. Future work should
either resolve them in a follow-up overhaul or adopt the documented
guidance here.

### 12.1 ParseError event shape

The parser currently emits `TextEvent` and `TagEvent`. Mismatched close
tokens and unclosed tags at flush are described as "error events" but
the dataclass shape is not finalized. Options:

- Add `ParseError` to the `ParseEvent` union with fields
  `(reason: str, position: int, expected: Optional[str], got: str)`.
- Surface errors via a separate `errors() -> List[ParseError]`
  accessor, leaving the event stream pure.

Recommendation: third event type in the union; consumers can choose to
ignore. Confirm in Phase 1.

### 12.2 Tool result message shape

Whether tool-call results become their own utility message
(`tag_type=TOOL_RESULT` or similar) or live as a separate role is
unresolved. Two viable options:

- New `tag_type` value `TOOL_RESULT`; result lives as a utility
  message attached to the same source assistant message via
  `source_message_id`.
- New `Role.TOOL_RESULT`; result is a separate row in the
  conversation, referenced by id.

Recommendation: utility message with a new tag type. Keeps utility as
"derived from an assistant message" and results as a sibling of the
call. Confirm in Phase 6.

### 12.3 Native function-call API integration

When an architecture supports the provider's native tool-calling API,
tool calls don't appear in the streamed text. The agent loop bypasses
the parser for those calls and constructs utility messages directly
from the structured fields the architecture surfaces. The
`Registry.execute_tool` path is identical; only the source of the
`(name, raw_payload)` pair differs.

This is supported by the new design without further changes; explicit
documentation will be added during Phase 6.

### 12.4 JSON Schema for native tools

`ArgumentDefinition` is kept for native tools per §2.10. If a future
need arises to expose native tools to the OpenAI / Anthropic native
tool-call APIs, a translator (`ArgumentDefinition` → JSON Schema) lives
in the simple protocol or in the architecture layer. This is a
forward-only translation; no canonical JSON Schema for native tools.

### 12.5 Tokenizer-aware tag tokens

Some models tokenize tag delimiters as single special tokens; the
emitted text form may differ. Currently we hardcode the text form per
model definition. A future enhancement could derive token strings from
the model's tokenizer. Not in scope.

### 12.6 Self-closing tags

XML self-closing form (`<reference guid="x" />`) is not supported in
the first cut. Easy to add by allowing `attribute_terminator` to be a
list of terminators with one of them marked self-closing. Add when a
real need surfaces.

### 12.7 Opaque content tags

There may eventually be tag types whose content is guaranteed to not
contain nested tags (e.g., a `<code>` block). For now the parser
always scans for nested opens. If false matches inside such content
become a problem, add an `opaque: bool` flag to `TagSpec` that
suppresses nested-open scanning until the matching close.

### 12.8 Order of tool collisions across protocols

First-in-list-wins per §2.8 is the documented policy. If priority
conflicts become a real configuration concern, a follow-up can add an
explicit `priority: int` field on `ProtocolInfo` or a config-level
ordering directive. Not in scope now.

### 12.9 Multiple instances of one protocol

A user might want two MCP "protocols" each pointing at a disjoint set
of servers, or to namespace MCP servers under different prefixes.
Pluggy's entry-point model loads one instance per registered class.
Multi-instance is achievable via configuration (the single MCP
protocol carries multiple servers internally), which is the assumed
shape. If true multi-instance becomes necessary, framework changes are
required; out of scope.

---

## 13. File-by-file changes summary

For quick reference during implementation. Not exhaustive — additional
small edits to imports, `__all__`, etc. expected.

### New files

- `src/claia/core/parsers/__init__.py`
- `src/claia/core/parsers/types.py`
- `src/claia/core/parsers/defaults.py`
- `src/claia/core/parsers/streaming.py`
- `src/claia/core/parsers/attributes.py`
- `src/claia/core/parsers/resolution.py`
- `src/claia/core/parsers/README.md`
- `src/claia/core/tools/types.py` (or extend `claia/core/plugins/base.py`)
  for `ToolReference`
- `src/claia/core/tools/protocols/simple/__init__.py`
- `src/claia/core/tools/protocols/simple/protocol.py`
- `src/claia/core/tools/protocols/simple/dispatcher.py`
- `src/claia/core/tools/protocols/simple/payload.py`
- `src/claia/core/tools/protocols/simple/README.md`
- (Phase 8) `src/claia/core/tools/protocols/mcp/...`
- Tests under `src/tests/` mirroring the above.

### Modified files

- `src/claia/core/plugins/base.py` — `ProtocolInfo` unchanged in shape;
  potentially add `ToolReference` and tag-related dataclasses if we
  centralize them here.
- `src/claia/core/data/...` (Conversation/Message) — new role and
  fields; serializers updated.
- `src/claia/core/definitions/model_definition.py` —
  `tag_overrides` field.
- `src/claia/framework/hooks/protocol.py` — new hookspecs.
- `src/claia/framework/registrars.py` — `ProtocolRegistrar` updated;
  `PatternRegistrar` removed.
- `src/claia/framework/manager.py` — protocol lifecycle hooks
  (`start`/`stop`/`refresh`); pattern PM and loader removed; tool
  index assembly added or moved here from `Registry`.
- `src/claia/framework/registry.py` — major rewrite of tool API
  (see §7); `process_content` removal.
- `pyproject.toml` — `claia.tool_patterns` entry-point group removed.

### Deleted files

- `src/claia/core/tools/patterns/__init__.py`
- `src/claia/core/tools/patterns/base.py`
- `src/claia/core/tools/patterns/default.py`
- `src/claia/core/tools/patterns/README.md`
- `src/claia/framework/hooks/pattern.py`
- `src/claia/core/tools/protocols/simple.py` (replaced by package).
- `src/claia/core/tools/protocols/base.py` (replaced by new ABC; may be
  retained transitionally then deleted at end of Phase 4).

---

## 14. Glossary

- **TagType** — categorical kind of a parsed span (TOOL, THINKING,
  REFERENCE, …). Stable identifier used for downstream dispatch.
- **TagSpec** — concrete description of one tag's open/close tokens
  and whether attributes are parsed.
- **TagEvent / TextEvent / ParseEvent** — output items from the
  streaming parser.
- **Utility message** — a sibling message of role `UTILITY` carrying a
  parsed span; references its source assistant message by id.
- **ToolReference** — protocol-agnostic description of a tool that the
  registry stores in its index. The registry never holds the tool's
  callable; dispatch goes through the owning protocol.
- **Qualified name** — fully-namespaced tool name in the registry's
  index. Native tools: `module.tool`. MCP tools:
  `mcp.<server>.<tool>`. Other protocols may use other prefixes.
- **Protocol** — a tool-execution backend. Owns its own tool
  inventory and dispatch logic. The simple protocol bridges native
  `BaseToolModule` plugins; the MCP protocol bridges remote MCP
  servers.
