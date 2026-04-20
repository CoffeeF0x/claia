# Tests

Pytest-based tests, organised to mirror the three subpackages under the
`claia` namespace.

Layout:
- `core/` — tests for `claia.core` (data models, plugin contracts,
  results, enums).
- `framework/` — tests for `claia.framework` (`Registry`, `Process`,
  `ProcessQueue`, agents, hooks, manager).
- `cli/` — tests for `claia.cli` (commands, settings, argument parsing).
- `conftest.py` — shared fixtures used across packages.
