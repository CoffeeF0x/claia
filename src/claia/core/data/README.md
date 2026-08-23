# Data

Pure CLAIA data models for IO and conversation state. Nothing here owns persistence; callers serialize models or observe events and store them wherever their runtime needs.

## What Lives Here

- `common/` — `DataObject` (shared `type` / `format` / `name` / `metadata`)
- `artifacts/` — durable IO payloads: text, image, audio, file, link, raw, tool
- `chunks/` — streamed content: text, image, audio, raw, tool, usage, metrics
- `request.py` — `AgentRequest`
- `response.py` — `AgentResponse` (iterate for chunks; then the aggregate)
- `models/` — `Conversation`, `Message`, `MessageSequence`, `MessageSequenceOrdered`, `Prompt`
- `events.py` — `DomainEvent` / `EventType`
- `utils/` — text, image, and tool-call parsing helpers

MIME enums live in `claia.core.enums.data` (`MediaType`, `TextFormat`, `ArtifactType`, …).

## Model boundary

**Conversation → `to_model_inputs` → `MessageSequence` or artifact list → deployment / `AgentResponse`.**

`ModelDefinition.inputs` lists `ArtifactType` values and optional complex types (`MessageSequence` / `MessageSequenceOrdered`). `outputs` lists the chunk classes the model is designed to yield. The conversation builds the sequence or takes artifacts from the latest message. Deployments do not see the conversation.

```python
from claia.core.data import Conversation, MessageSequence
from claia.core.definitions.model_definition import ModelDefinition
from claia.core.enums.conversation import MessageRole
from claia.core.enums.data import ArtifactType

conversation = Conversation(title="Example")
conversation.add_message(MessageRole.USER, "Hello")
inputs = conversation.to_model_inputs(
  ModelDefinition(inputs=[ArtifactType.TEXT, MessageSequence]),
  system="Be brief",
)
```

See `claia/reference/` in the ExoFox docs repo.
