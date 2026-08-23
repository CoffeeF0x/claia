# Conversation Models

Conversation models represent chat state as a pure Python message tree with an event-backed audit trail. They are the data contract used by the framework, CLI, agents, and host integrations.

## What Lives Here

- `conversation.py` — `Conversation`, including title, messages, active branch tracking, serialization, event emission, and `to_model_inputs`.
- `message.py` — `Message`, including role, content, attachments, parent links, and thread-safe content updates.
- `message_sequence.py` — generate-time `MessageSequence` / `MessageSequenceOrdered` views (system is a `SYSTEM` turn).
- `tool_definition.py` — compatibility re-export for tool definition dataclasses.

All primary types are available from `claia.core.data`; `Conversation` and `Message` are also re-exported from `claia.framework`.

## How It Fits

- Messages form a tree via `parent_id`; `active_head_id` points at the current branch tip.
- Mutations record `DomainEvent`s for auditing and host-runtime persistence.
- Streaming updates can append chunks without flooding the event log.
- Generation settings stay outside the data model and are passed at runtime through registry or process parameters.
- `to_model_inputs` is the generate-time translation: a filtered message sequence (tool-result utilities included) or the latest message's artifacts. Deployments receive that result, not the conversation. Architectures format the sequence.

## Quick Example

```python
from claia.core.data import Conversation
from claia.core.enums.conversation import MessageRole

conversation = Conversation(title="My Conversation")
conversation.add_message(MessageRole.USER, "Hello!")
conversation.add_message(MessageRole.ASSISTANT, "Hi there!")

for message in conversation.get_thread():
    print(message.role.value, message.content)

payload = conversation.to_dict()
loaded = Conversation.from_dict(payload)
print(loaded.title, len(loaded.messages))
```

Use `conversation.observe(callback)` when an integration needs to react to each mutation. Use `conversation.pull_events()` when the caller owns the persistence boundary and wants to flush events later.
