# CLI Storage

CLI-owned JSON persistence for local CLAIA sessions. This package is intentionally small and is not the core persistence contract for library consumers.

## What Lives Here

- `json_store.py` — `JsonStore`, an atomic JSON file store for artifacts.
- `__init__.py` — re-exports `JsonStore`.

## How It Fits

`JsonStore` saves serialized artifacts into type-specific directories:

- `conversations/`
- `prompts/`
- `texts/`
- `images/`
- `audio/`

Use it when working inside the CLI runtime. External apps should persist `claia.core.data` models through their own database, object store, or API boundary.

```python
from claia.cli.storage import JsonStore
from claia.core.data import Conversation

store = JsonStore("./storage")
conversation = Conversation(title="Local chat")

store.save(conversation)
loaded = store.load(conversation.id)
```
