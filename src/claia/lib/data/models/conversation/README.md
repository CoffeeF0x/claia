# Conversation Models

Pure data models for conversations, built on top of the media/data layer.

## What lives here

- `conversation.py` — `Conversation` model (title, prompt, messages, actions, settings).
- `message.py` — `Message` model with thread-safe operations.
- `action.py` — `Action` model for audit trail events.
- `conversation_settings.py` — `ConversationSettings` configuration object.

All are re-exported via `claia.lib.data` (see `lib/data/__init__.py`).

## How it fits (TL;DR)

- `Conversation` extends `TextFile` so it can be stored with the same repository infrastructure as other files.
- Repositories live in `lib/data/repositories` and operate on `BaseFile`/`TextFile` and subclasses.
- The rest of CLAIA (agents, registry, CLI) treats `Conversation` as a pure in-memory model; persistence is optional.

## Quick usage example

```python
from claia.lib.data import Conversation, FileRepository
from claia.lib.enums.conversation import MessageRole

# Create a conversation
conv = Conversation(title="My Conversation")
conv.add_message(MessageRole.USER, "Hello!")
conv.add_message(MessageRole.ASSISTANT, "Hi there!")

# Persist via generic file repository
repo = FileRepository.create_file_system("/conversations")
repo.save(conv)

loaded = repo.load(conv.id, load_content=True)
print(loaded.title, len(loaded.messages))
```

For more details on methods and behavior (streaming, audit trail, thread safety), see
`conversation.py`, `message.py`, and `action.py`.
