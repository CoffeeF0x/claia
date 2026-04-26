# Source Tree

This directory contains the Python source for CLAIA.

- Package: `claia/` — namespace package containing the framework layers
  - `claia/core/` — pure library types, plugin contracts, model implementations, definitions, deployments, solvers, and tools
  - `claia/framework/` — plugin manager, registry facade, processes, queues, workers, and agents
  - `claia/cli/` — command-line application, settings, command handlers, rendering, and CLI-owned storage
- Tests: `tests/` — pytest-based test suite

Entrypoints:
- `python -m claia.cli` — run the CLI from source
- `claia` — console script if installed via pip
