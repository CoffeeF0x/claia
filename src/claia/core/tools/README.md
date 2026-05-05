# Tools

The tool system lets models call structured commands. It splits into
**modules** (tool authors' surface) and **protocols** (the dispatch
backends that own execution). The agent loop drives a streaming
[`TagParser`](../parser/README.md) per turn and routes parsed
`TOOL`-tag events through `Registry.execute_tool`.

## What Lives Here

- `modules/` — concrete tool groups such as the `sample` and `system`
  tools. Each module is a `BaseToolModule` plugin published through
  the `claia.tool_modules` entry point.
- `protocols/` — dispatch backends for the unified tool contract.
  `simple/` bridges native `BaseToolModule` plugins; future protocols
  (MCP, …) plug in here.

## How It Fits

1. Tool modules publish `ToolDefinition`s.
2. `Manager` instantiates each `claia.tool_protocols` plugin and hands
   the loaded `BaseToolModule` instances to those that opt into
   `bind_tool_modules` (currently only the simple protocol).
3. `Registry` builds a unified `qualified_name -> ToolReference` index
   by walking `protocol.get_tool_references()` across every loaded
   protocol (plan §7.1).
4. The agent loop (see `framework/agents/simple.py`) constructs a
   `TagParser` per turn, parses streamed model output, and emits a
   utility message for each closed tag. Tool tags are dispatched
   through `Registry.execute_tool(qualified_name, raw_payload, conversation)`,
   which routes to the owning protocol's `execute`.
5. The simple protocol JSON-decodes the payload, prepares the
   callable's kwargs, runs it, and normalizes the return into a
   `Result`. Tool output is streamed back into the active assistant
   message inline.

CLI direct execution (`Registry.run_command(name, parameters, conversation, **kwargs)`)
preserves a parameter-dict-style entry point for non-streaming
callers; the dispatcher helpers are shared with the simple protocol so
type coercion stays consistent.

Register extensions through the `claia.tool_modules` and
`claia.tool_protocols` entry points.
