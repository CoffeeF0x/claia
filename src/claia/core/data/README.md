# Data

Pure CLAIA data models for IO and conversation state. Nothing here owns persistence; callers serialize models or observe events and store them wherever their runtime needs.

## What Lives Here

- `common/` — `DataObject` (shared `type` / `format` / `name` / `metadata`)
- `artifacts/` — durable IO payloads: text, image, audio, file, link, raw
- `chunks/` — streamed content: text, image, audio, raw
- `response.py` — `ModelResponse` (chunks + complete/error)
- `adapters.py` — Conversation ↔ artifacts helpers
- `models/` — `Conversation`, `Message`, `Prompt` (not IO artifacts)
- `events.py` — `DomainEvent` / `EventType`
- `utils/` — text, image, and tool-call parsing helpers

MIME enums live in `claia.core.enums.data` (`MediaType`, `TextFormat`, …).

## Model boundary

**Artifacts in → `ModelResponse` out.** Deployments flatten a `Conversation` to artifacts, call `model.generate`, and stream `BaseChunk` content. Status is on `ModelResponse`, not control chunks.

```python
from claia.core.data import Conversation, TextArtifact, ModelResponse
from claia.core.data.adapters import conversation_to_artifacts
from claia.core.enums.conversation import MessageRole

conversation = Conversation(title="Example")
conversation.add_message(MessageRole.USER, "Hello")
artifacts = conversation_to_artifacts(conversation)
```

See [docs/data-architecture.md](../../../../docs/data-architecture.md).
