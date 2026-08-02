# Data

Pure CLAIA data models for IO and conversation state. Nothing here owns persistence; callers serialize models or observe events and store them wherever their runtime needs.

## What Lives Here

- `common/` — `DataObject` (shared `type` / `format` / `name` / `metadata`)
- `artifacts/` — durable IO payloads: text, image, audio, file, link, raw, tool
- `chunks/` — streamed content: text, image, audio, raw
- `response.py` — `ModelResponse` (chunks + complete/error)
- `models/` — `Conversation`, `Message`, `MessageSequence`, `Prompt` (not IO artifacts)
- `events.py` — `DomainEvent` / `EventType`
- `utils/` — text, image, and tool-call parsing helpers

MIME enums live in `claia.core.enums.data` (`MediaType`, `TextFormat`, `ArtifactType`, `SequenceKind`, …).

## Model boundary

**Conversation → deployment.translate → `MessageSequence` → `ModelResponse`.**
Deployments own translation using `ModelDefinition.supported_artifacts` and `sequence_kind`. Models consume sequences only.

```python
from claia.core.data import Conversation
from claia.core.definitions.model_definition import ModelDefinition
from claia.core.deployments.dummy import DummyDeploymentPlugin
from claia.core.enums.conversation import MessageRole

conversation = Conversation(title="Example")
conversation.add_message(MessageRole.USER, "Hello")
sequence = DummyDeploymentPlugin().translate(conversation, ModelDefinition())
```

See [docs/data-architecture.md](../../../../docs/data-architecture.md).
