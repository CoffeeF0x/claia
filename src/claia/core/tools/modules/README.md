# Tool Modules

Concrete tool integrations providing callable commands (the “tools” the model can call).

## What lives here

- `sample.py` — sample module with multiple tools (`current_time`, `add`, `subtract`, `echo`).
- `system.py` — terminal/CLI utilities (`clear`, `exit`).

Each module subclasses `BaseToolModule` from `claia.core.tools.modules.base` and exposes a class-level `info: ToolModuleInfo` attribute plus a `get_module_tools()` method. The framework layer wraps it in a `ToolModuleRegistrar` that adds the `@hookimpl` markers pluggy needs, so the core plugin itself stays pluggy-free.

## How tools fit in

- Tool modules are discovered via the `claia.tool_modules` entry point.
- `Manager` builds a per-module **commands catalog** (`get_all_commands()`) by calling each module's hooks; the CLI uses this for the `:tool` / `:help` listings.
- The built-in **simple** protocol consumes that catalog, registers a `ToolReference` per tool with the `Registry`, and dispatches calls.
- Streaming tool-call extraction lives in `claia.core.parser` (`TagParser`); the agent loop drives the parser and routes `TOOL`-tag events through `Registry.execute_tool`.

## Implementing a new tool module (TL;DR)

1. Subclass `BaseToolModule` and declare:
   - a class-level `info = ToolModuleInfo(name, title, description, params=[...])` (each `ParamSpec` in `params` describes a kwarg the module consumes).
   - `get_module_tools() -> Dict[str, ToolDefinition]`.
2. For each tool:
   - define a `ToolDefinition` with `name`, `description`, `callable`, and `arguments` (`ArgumentDefinition`).
   - the callable can return `Result`, a string, or arbitrary data (wrapped by `Result`).
3. Register the module via the `claia.tool_modules` entry point so `Manager` can discover it.
