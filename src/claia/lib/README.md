# Library

Shared runtime library for agents and models.

- `base.py` — base agent structures/utilities
- `files/` — file/prompt/conversation abstractions
- `model/` — model architecture layer (API/transformers/dummy)
- `process.py`, `queue.py`, `results.py` — orchestration utilities

Note: architecture components live under `lib/model/` to avoid base naming conflicts.
