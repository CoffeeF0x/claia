# Data

Pure CLAIA data models for IO and conversation state. Nothing here owns persistence; callers serialize models or observe events and store them wherever their runtime needs.

## What Lives Here

- `common/` — `DataObject` (shared `type` / `format` / `name` / `metadata`)
- `artifacts/` — durable IO payloads: text, image, audio, file, link, raw, tool
- `chunks/` — streamed content: text, image, audio, raw
- `response.py` — `ModelResponse` (chunks + complete/error)
- `models/` — `Conversation`, `Message`, `MessageSequence`, `MessageSequenceOrdered`, `Prompt`
- `events.py` — `DomainEvent` / `EventType`
- `utils/` — text, image, and tool-call parsing helpers

MIME enums live in `claia.core.enums.data` (`MediaType`, `TextFormat`, `ArtifactType`, …).

## Model boundary

**Conversation → deployment.translate → `MessageSequence` or artifact list → `ModelResponse`.**

`ModelDefinition.supported_inputs` lists `ArtifactType` values and optional complex types (`MessageSequence` / `MessageSequenceOrdered`). Deployments choose the sequence class or extract artifacts from the latest message.

```python
from claia.core.data import Conversation, MessageSequence
from claia.core.definitions.model_definition import ModelDefinition
from claia.core.deployments.dummy import DummyDeploymentPlugin
from claia.core.enums.conversation import MessageRole
from claia.core.enums.data import ArtifactType

conversation = Conversation(title="Example")
conversation.add_message(MessageRole.USER, "Hello")
inputs = DummyDeploymentPlugin().translate(
  conversation,
  ModelDefinition(supported_inputs=[ArtifactType.TEXT, MessageSequence]),
)
```

See `claia/data-architecture.md` in the ExoFox docs repo.
