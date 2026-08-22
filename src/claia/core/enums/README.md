# Enums

Typed enumerations used across the runtime.

## What lives here

- `command.py` — CLI command execution priority.
- `conversation.py` — message roles.
- `data/` — media types, format subtypes, artifact contracts.
- `events.py` — conversation domain event types.
- `file.py` — file subdirectories, status, and MIME mappings.
- `logging.py` — log levels and formats.
- `model.py` — model capabilities, IO types, source preference.
- `parser.py` — categorical tag kinds (`TagType`).
- `plugins.py` — parameter scope and settings categories.
- `task.py` — task status and task callback events.
- `task_queue.py` — task-queue lifecycle hooks.

Enums keep cross-package contracts explicit and avoid stringly-typed code.
