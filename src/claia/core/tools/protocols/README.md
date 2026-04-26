# Tool Protocols

Protocols define **how tool commands are executed** once a pattern has detected them.

## What lives here

- `simple.py` — basic protocol that:
  - looks up a tool in the provided **commands catalog**
  - invokes the tool’s callable with prepared kwargs
  - returns a `Result` object.

Protocols implement the contract mirrored by `claia.framework.hooks.protocol` and are discovered via the
`claia.tool_protocols` entry point.

## How protocols fit in

- `Registry.process_content(...)`:
  1. Uses a **tool pattern** to find tool calls in text.
  2. Prepares arguments for the target tool using its `ToolDefinition`.
  3. Calls the selected protocol’s `execute(...)`, passing:
     - tool name
     - prepared kwargs
     - conversation
     - **commands catalog** from `Registry.get_commands_catalog()`.
  4. Replaces the original tool call text with the protocol’s output.

Swap in a different protocol to change execution behavior (e.g., batching, sandboxing, retries)
without changing patterns or tool modules.
