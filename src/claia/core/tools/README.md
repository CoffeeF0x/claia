# Tools

The tool system lets models call structured commands. It is split into modules that provide commands, patterns that detect calls in text, and protocols that execute matched calls.

## What Lives Here

- `modules/` — concrete command groups such as sample and system tools.
- `patterns/` — parsers that detect tool-call blocks in model output.
- `protocols/` — dispatch logic that validates and runs commands from the catalog.

## How It Fits

1. Tool modules publish `ToolDefinition`s.
2. `Manager` builds a command catalog from loaded modules.
3. A pattern finds tool-call text in a model response.
4. A protocol executes the requested command and returns the result text.
5. `Registry.process_content(...)` coordinates detection, execution, and replacement.

Register extensions through `claia.tool_modules`, `claia.tool_patterns`, and `claia.tool_protocols` entry points.
