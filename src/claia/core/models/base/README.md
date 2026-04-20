# Model Base

Shared model interfaces and base classes.

## What lives here

- `base.py` — abstract base model (core interface).
- `api.py` — base for API-backed models.
- `local.py` — base for local/transformer models.

Concrete models in `api/`, `transformers/`, and `dummy/` build on these types.
