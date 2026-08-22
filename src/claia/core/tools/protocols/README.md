# Tool Protocols

Protocols define **how tool calls are executed** once the agent loop's
streaming `TagParser` produces a `TagEvent` of type `TOOL`.

## What lives here

- `simple/` — package implementing `SimpleProtocol`, the
  in-tree default. Bridges native `BaseToolModule` plugins through
  the unified protocol contract; see the package README for the
  internal split (`protocol.py` / `dispatcher.py` / `payload.py`).
- `base.py` — the `BaseProtocol` ABC. Every protocol exposes:
  - `start()` / `stop()` / `refresh()` — lifecycle hooks (default
    no-ops; MCP and similar implementations open / refresh sessions
    here).
  - `get_tool_references() -> List[ToolReference]` — the protocol's
    advertised tool inventory. Returned references are pooled into
    the registry's unified tool index.
  - `execute(qualified_name, raw_payload, conversation, **kwargs) -> Result`
    — dispatch sink. The protocol decodes `raw_payload` according to
    its own conventions (JSON for the simple protocol, MCP envelopes
    for MCP) and runs the underlying tool.

## How protocols fit in

1. The framework loads each `claia.tool_protocols` plugin from
   entry points. The simple protocol additionally has its native tool
   modules bound by the manager via `bind_tool_modules`.
2. After load, the manager calls `start()` on every protocol so
   session-bearing implementations can open their resources.
3. `Registry._rebuild_tool_index` walks
   `protocol.get_tool_references()` across all loaded protocols and
   builds a `qualified_name -> ToolReference` index. First-in-list
   wins on collisions.
4. Inside the agent loop the streaming `TagParser` emits a
   `TagEvent` for each closed tag. For TOOL events the agent calls
   `Registry.execute_tool(qualified_name, raw_payload, conversation, **kwargs)`,
   which forwards to the owning protocol's `execute(...)`. The
   result text is appended to the streaming assistant message and
   emitted as ``ProcessEvent.TOKEN`` so terminal renderers see the call
   → response flow inline.

Swap in a different protocol to change execution behavior — batching,
sandboxing, remote MCP servers — without touching the agent loop or
the registry's index assembly.
