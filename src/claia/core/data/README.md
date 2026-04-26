# Data

Pure CLAIA data models: artifacts, prompts, conversations, messages, and domain events. Nothing here owns persistence; callers serialize models or observe events and store them wherever their runtime needs.

## What Lives Here

- `models/` — `BaseArtifact`, `TextArtifact`, `ImageArtifact`, `AudioArtifact`, `Prompt`, `Conversation`, and `Message`.
- `events.py` — `DomainEvent` and `EventType`, the audit/runtime event stream for mutable models.
- `utils/` — text, image, and tool-call parsing helpers.

`claia.core.data` re-exports the main model and event types. `claia.framework` re-exports the common ones too for app code that already imports the registry from there.

## How It Fits

- Artifacts carry identity, metadata, timestamps, optional source references, and in-memory content.
- `Conversation` extends `TextArtifact` and stores a message tree plus an event log.
- Host runtimes such as the CLI, an API server, or a worker decide how to persist serialized dicts and when to flush events.

Generation parameters do not live on `Conversation`. Architectures and models declare runtime `ParamSpec`s, and callers pass values through `Registry.run(..., **kwargs)` or `Process.parameters`.

## Quick Example

```python
from claia.core.data import Conversation, TextArtifact
from claia.core.enums.conversation import MessageRole

text = TextArtifact.from_content("Hello, world!", name="greeting.txt")

conversation = Conversation(title="Example")
conversation.add_message(MessageRole.USER, "Summarize the greeting.")

payload = conversation.to_dict()
restored = Conversation.from_dict(payload)

print(text.content)
print(restored.get_thread()[0].content)
```

Use `Conversation.observe(callback)` for push-style persistence hooks, or `Conversation.pull_events()` when you want to drain pending events at request boundaries.
