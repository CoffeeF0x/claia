"""Sanity: exercise model implementations standalone (no Registry).

Start here with DummyModel. Swap MODULE / run_* helpers as more models
are validated. Keep this file minimal and disposable.
"""

from claia.core.data import Conversation, ModelResponse, TextChunk
from claia.core.data.models.conversation.message_sequence import MessageSequence
from claia.core.definitions.model_definition import ModelDefinition
from claia.core.deployments.dummy import DummyDeployment
from claia.core.enums.conversation import MessageRole
from claia.core.enums.data import ArtifactType
from claia.core.models.dummy import DummyModel

MODULE = DummyModel

# Visible streaming for manual sanity runs (DummyModel defaults).
STREAM_KWARGS = {
  "chars_per_second": 2000,
  "chars_per_chunk": 20,
}


def drain(generator):
  """Collect yielded chunks and the generator's return value."""
  chunks = []
  try:
    print("\nDraining generator...\n")
    while True:
      chunk = next(generator)
      text = chunk.data if isinstance(chunk, TextChunk) else str(chunk)
      print(text, end="", flush=True)
      chunks.append(chunk)
  except StopIteration as stop:
    print("\nGenerator drained.\n\n")
    return chunks, stop.value


def _definition():
  return ModelDefinition(
    inputs=[ArtifactType.TEXT, MessageSequence],
  )


def run_model():
  """Construct DummyModel directly and stream a response."""
  model = MODULE(model_name="dummy-model")
  conversation = Conversation(title="sanity-models")
  conversation.add_message(MessageRole.USER, "Tell me a story.")
  sequence = DummyDeployment().translate(conversation, _definition())
  message_count_before = len(conversation.messages)

  print(f"model: {model.model_name} ({type(model).__name__})")
  print(f"story length: {model.story_length} chars")
  print(f"sequence turns: {len(sequence)} ({type(sequence).__name__})")
  print()

  chunks, response = drain(model.generate(sequence, **STREAM_KWARGS))

  assert isinstance(response, ModelResponse)
  preview = response.text()[:120].replace("\n", " ")
  print(f"chunks: {len(chunks)}")
  print(f"response.complete: {response.complete}")
  print(f"response.error: {response.error}")
  print(f"yielded chars: {sum(len(c.data) for c in chunks if isinstance(c, TextChunk))}")
  print(f"preview: {preview}...")
  print(f"conversation untouched: {len(conversation.messages) == message_count_before}")
  print()


def run_deployment():
  """Conversation → deployment.translate → generate (streamed)."""
  deployment = DummyDeployment()
  info = deployment.info
  conversation = Conversation(title="sanity-models-deploy")
  conversation.add_message(MessageRole.USER, "Tell me a story.")

  print(f"deployment: {info.name} - {info.description}")

  chunks, _ = drain(deployment.run(
    model_name="dummy-model",
    model_class=MODULE,
    conversation=conversation,
    cache={},
    init_kwargs={},
    runtime_kwargs=STREAM_KWARGS,
    definition=_definition(),
  ))

  preview = "".join(
    c.data for c in chunks if isinstance(c, TextChunk)
  )[:120].replace("\n", " ")
  print(f"chunks: {len(chunks)}")
  print(f"yielded chars: {sum(len(c.data) for c in chunks if isinstance(c, TextChunk))}")
  print(f"preview: {preview}...")
  print()


if __name__ == "__main__":
  print("Starting...")
  run_model()
  run_deployment()
