# CLAIA Package

Core package implementing agents, model stack, tool system, and plugin registries.

Key modules:
- `manager.py` — plugin manager (models, tools, agents)
- `registry.py` — shared registry utilities

Subpackages:
- `agents/` — agent implementations
- `cli/` — command-line entrypoints and settings
- `deployments/` — runtime backends (api, local, remote, dummy)
- `hooks/` — plugin hook contracts
- `lib/` — shared runtime library (files, process/queue, model abstractions)
- `architectures/` — architecture adapters
- `definitions/` — model metadata/definitions
- `solvers/` — solver strategies
- `tool_modules/` — concrete tool integrations
- `tool_patterns/` — high-level tool invocation patterns
- `tool_protocols/` — protocols for executing tool commands

Run: `python -m claia` (delegates to `cli`).
