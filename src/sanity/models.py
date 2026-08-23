"""Sanity: exercise model implementations standalone (no Registry).

Start here with DummyArchitecture. Swap MODULE / run_* helpers as more
models are validated. Keep this file minimal and disposable.
"""

from claia.core.architectures.dummy.dummy import DummyArchitecture
from claia.core.data import AgentRequest, Conversation, ModelResponse, TextChunk
from claia.core.data.models.conversation.message_sequence import MessageSequence
from claia.core.definitions.model_definition import ModelDefinition
from claia.core.deployments.dummy import DummyDeployment
from claia.core.enums.conversation import MessageRole
from claia.core.enums.data import ArtifactType

MODULE = DummyArchitecture

# Visible streaming for manual sanity runs (DummyArchitecture defaults).
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


def _request(inputs, **args):
  return AgentRequest(
    model="dummy",
    provider_model="dummy-model",
    architecture_class=MODULE,
    deployment=None,
    inputs=inputs,
    args=args,
  )


def run_model():
  """Construct DummyArchitecture directly and stream a response."""
  model = MODULE(model_name="dummy-model")
  conversation = Conversation(title="sanity-models")
  conversation.add_message(MessageRole.USER, "Tell me a story.")
  sequence = conversation.to_model_inputs(_definition())
  message_count_before = len(conversation.messages)

  print(f"model: {model.model_name} ({type(model).__name__})")
  print(f"story length: {model.story_length} chars")
  print(f"sequence turns: {len(sequence)} ({type(sequence).__name__})")
  print()

  chunks, response = drain(model.generate(_request(sequence, **STREAM_KWARGS)))

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
  """Conversation → to_model_inputs → deployment.run (streamed)."""
  deployment = DummyDeployment()
  info = deployment.info
  conversation = Conversation(title="sanity-models-deploy")
  conversation.add_message(MessageRole.USER, "Tell me a story.")

  print(f"deployment: {info.name} - {info.description}")

  request = AgentRequest(
    model="dummy",
    provider_model="dummy-model",
    architecture_class=MODULE,
    deployment=deployment,
    inputs=conversation.to_model_inputs(_definition()),
    args=STREAM_KWARGS,
  )
  instance = deployment.deploy(request)
  chunks, _ = drain(deployment.run(instance, request))

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
