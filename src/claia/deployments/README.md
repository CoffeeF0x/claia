# Deployments

Runtime backends that define how/where models run.

- `api.py` — API-based execution
- `local.py` — local runtime
- `remote.py` — remote runtime
- `dummy.py` — no-op/testing backend

Each deployment advertises `required_args` for safe kwargs filtering.
