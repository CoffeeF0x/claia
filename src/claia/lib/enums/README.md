# Enums

Typed enumerations used across the runtime.

## What lives here

- `conversation.py` — roles, action kinds.
- `file.py` — file and MIME types.
- `logging.py` — log levels/categories.
- `model.py` — model/provider/types.
- `process.py` — process and task states.

Enums are used to keep cross-package contracts explicit and avoid stringly-typed code.
