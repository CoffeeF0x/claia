# Hooks

Pluggy hook contracts and info objects for all CLAIA plugin types.

## What lives here

- `agent.py` — hooks and `AgentInfo` for agent plugins.
- `architecture.py` — hooks and `ArchitectureInfo` for architecture plugins.
- `definition.py` — hooks and `ModelDefinition` pattern for model metadata.
- `deployment.py` — hooks and `DeploymentInfo` for deployments.
- `protocol.py` — hooks, `ProtocolInfo`, and `ToolReference` for tool protocols.
- `solver.py` — hooks and `SolverInfo`/`DeploymentParams` for solvers.
- `tool.py` — hooks and `ToolModuleInfo`/`ToolDefinition`/`ArgumentDefinition` for tool modules.

## How hooks fit in

- Each plugin type has:
  - a **hookspec** module here
  - a **PluginManager** in `manager.py`
  - an **entry point group** (e.g., `claia.architectures`, `claia.tool_modules`).
- Plugins implement these hooks via `hookimpl` so the `Manager` and `Registry` can:
  - discover plugins
  - fetch metadata
  - call extension points in a uniform way.
