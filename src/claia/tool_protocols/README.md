# Tool Protocols

Protocols define how tool commands are executed.

- `simple.py` — resolves and invokes callables from a provided commands catalog (not full manager). Argument prep/validation is handled by the registry.

Breaking change: protocol `execute` receives a catalog from `ToolsRegistry.get_commands_catalog()`.
