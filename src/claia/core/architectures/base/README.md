# Architecture Base

Shared architecture interfaces and base classes.

## What lives here

- `base.py` — `BaseArchitecture`, the abstract generate contract and
  the `deployment` class attribute that links each family to the
  deployment serving it.
- `api.py` — `APIArchitecture`, base for hosted-API architectures
  (`deployment = "api"`; session, key and header handling).
- `local.py` — `LocalArchitecture`, base for weight-holding
  architectures (`deployment = "transformers"`; load/unload and
  device placement).

Concrete architectures in `api/`, `transformers/`, and `dummy/` build
on these types.
