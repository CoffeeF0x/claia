# CLAIA Package

Core runtime for agents, model stack, tool system, and plugin registries.

## What this package does (TL;DR)

- Turns **conversations + settings** into **model calls and tool executions**.
- Uses a **plugin system** (via `pluggy`) so models, tools, and agents can be added without changing core code.
- Provides a **single facade** (`Registry`) over the plugin `Manager` plus queues, processes, and results.

## Runtime flow (mental model)

1. **Entry**: `python -m claia` or the `cli` package parses CLI args and builds settings.
2. **Registry**: `registry.Registry` loads plugins via `manager.Manager` and exposes:
   - model API (`run(...)`)
   - tool API (`process_content(...)`, `run_command(...)`)
   - agent API (process queue + workers)
3. **Plugins**: concrete implementations live in subpackages and are discovered via entry points
   (`claia.architectures`, `claia.deployments`, `claia.tool_modules`, `claia.agents`, etc.).

Key modules:
- `manager.py` — plugin manager for models, tools, and agents
- `registry.py` — high-level façade used by CLI/apps to talk to the system

## Subpackages (where to look)

- `agents/` — agent implementations (how processes are orchestrated)
- `cli/` — command-line entrypoints, settings, and logging
- `deployments/` — runtime backends (API, local, remote, dummy)
- `hooks/` — pluggy hookspecs and info objects for all plugin types
- `lib/` — shared runtime library (data models, enums, process/queue, model abstractions)
- `architectures/` — architecture adapters wrapping concrete model APIs
- `definitions/` — model metadata/definitions consumed by solvers/deployments
- `solvers/` — deployment/architecture selection strategies
- `tools/` — concrete tool modules (command implementations)
- `tool_patterns/` — high-level tool invocation patterns (how tool calls are marked in text)
- `tool_protocols/` — protocols for executing tool commands against the command catalog

Run: `python -m claia` (delegates to `cli`).
