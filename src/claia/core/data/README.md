# Data

Pure CLAIA data models for IO and conversation state. Nothing here owns persistence; callers serialize models or observe events and store them wherever their runtime needs.

## What Lives Here

- `common/` — `DataObject` (shared `type` / `format` / `name` / `metadata`)
- `artifacts/` — durable IO payloads: text, image, audio, file, link, raw
- `chunks/` — streamed content: text, image, audio, raw
- `response.py` — `ModelResponse` (chunks + complete/error)
- `models/` — `Conversation`, `Message`, `Prompt` (not IO artifacts)
- `events.py` — `DomainEvent` / `EventType`
- `utils/` — text, image, and tool-call parsing helpers

MIME enums live in `claia.core.enums.data` (`MediaType`, `TextFormat`, …).

## Model boundary

**Artifacts in → `ModelResponse` out.** Deployments own the shared run path on `BaseDeployment` (`resolve_model`, `stream_generate`, `run`). A `Conversation` flattens via `to_artifacts()` before `model.generate`.

```python
from claia.core.data import Conversation
from claia.core.enums.conversation import MessageRole

conversation = Conversation(title="Example")
conversation.add_message(MessageRole.USER, "Hello")
artifacts = conversation.to_artifacts()
```

See [docs/data-architecture.md](../../../../docs/data-architecture.md).
