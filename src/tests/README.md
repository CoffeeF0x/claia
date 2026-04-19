# Tests

Pytest-based tests, organised to mirror the three packages.

Layout:
- `claia_core/` — tests for the pure-library layer (data models, plugin
  contracts, results, enums).
- `claia/` — tests for the framework layer (`Registry`, `Process`,
  `ProcessQueue`, agents, hooks, manager).
- `claia_cli/` — tests for the CLI application (commands, settings,
  argument parsing).
- `conftest.py` — shared fixtures used across packages.
