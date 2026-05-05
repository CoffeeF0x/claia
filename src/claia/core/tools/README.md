# Tools

The tool system lets models call structured commands. It splits into
modules that publish callables (the native tools), patterns that
detect tool-call blocks in legacy free-form output, and protocols
that own dispatch.

## What Lives Here

- `modules/` — concrete tool groups such as sample and system tools.
  Each module is a `BaseToolModule` plugin published through the
  `claia.tool_modules` entry point.
- `patterns/` — pre-overhaul detectors for tool-call blocks. Phase 7
  retires this subsystem in favor of the streaming
  [`TagParser`](../parser/README.md), which is now driven by the
  agent loop. The directory is kept for compatibility until the
  pattern PM and entry-point group are removed.
- `protocols/` — dispatch backends for the unified tool contract.
  `simple/` bridges native `BaseToolModule` plugins; future
  protocols (MCP, …) plug in here.

## How It Fits (post-overhaul)

1. Tool modules publish `ToolDefinition`s.
2. `Manager` instantiates each `claia.tool_protocols` plugin and
   hands the loaded `BaseToolModule` instances to those that opt
   into `bind_tool_modules` (currently only the simple protocol).
3. `Registry` builds a unified `qualified_name -> ToolReference`
   index by walking `protocol.get_tool_references()` across every
   loaded protocol (plan §7.1).
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
callers; the dispatcher helpers are shared with the simple protocol
so type coercion stays consistent.

Register extensions through the `claia.tool_modules` and
`claia.tool_protocols` entry points. The `claia.tool_patterns` group
is dormant until phase 7 removes it.
