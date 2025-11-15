# Library

Shared runtime library for agents and models.

## What lives here

- `base.py` — base agent structures/utilities.
- `data/` — pure data models (media, conversations) + repositories/utilities.
- `enums/` — typed enums shared across the runtime.
- `model/` — model architecture layer (API/transformers/dummy).
- `process.py`, `queue.py`, `results.py` — orchestration utilities and result helpers.

Architecture components live under `lib/model/` to avoid base naming conflicts.
