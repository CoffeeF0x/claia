# Tool Patterns

High-level patterns for **detecting and parsing tool calls** in model text.

## What lives here

- `default.py` — baseline pattern implementation and utilities.

Patterns typically implement hooks from `hooks.pattern` and are discovered via the
`claia.tool_patterns` entry point.

## How patterns fit in

- Define how tool calls are marked and extracted (e.g., special tags or JSON blocks).
- Provide methods such as `find_tool_calls(content, conversation, settings)` returning matches with:
  - tool name
  - parsed parameters
  - character offsets (for text replacement).
- Used by `Registry.process_content(...)` to:
  - scan assistant output for tool calls
  - hand off to a **tool protocol** for execution
  - splice results back into the content.
