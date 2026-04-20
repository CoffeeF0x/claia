# Tool Modules

Concrete tool integrations providing callable commands (the “tools” the model can call).

## What lives here

- `sample.py` — sample module with multiple tools (`current_time`, `add`, `subtract`, `echo`).
- `system.py` — terminal/CLI utilities (`clear`, `exit`).

Each module provides a **plugin class** implementing `claia.hooks.tool.ToolModuleHooks` via pluggy.

## How tools fit in

- Tool modules are discovered via the `claia.tool_modules` entry point.
- `Manager` builds a **commands catalog** by calling each module’s hooks.
- `Registry`:
  - exposes this catalog via `get_commands_catalog()`
  - uses **tool patterns** to detect tool calls in text
  - uses **tool protocols** to execute selected tools.

## Implementing a new tool module (TL;DR)

1. Create a plugin class with `hookimpl` methods:
   - `get_module_info() -> ToolModuleInfo` (name, title, description, `params: List[ParamSpec]`).
   - `get_module_tools() -> Dict[str, ToolDefinition]`.
2. For each tool:
   - define a `ToolDefinition` with `name`, `description`, `callable`, and `arguments` (`ArgumentDefinition`).
   - the callable can return `Result`, a string, or arbitrary data (wrapped by `Result`).
3. Register the module via the `claia.tool_modules` entry point so `Manager` can discover it.
