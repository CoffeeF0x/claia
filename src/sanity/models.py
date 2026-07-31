"""Sanity: exercise model implementations standalone (no Registry).

Start here with DummyModel. Swap MODULE / run_* helpers as more models
are validated. Keep this file minimal and disposable.
"""

from claia.core.data import Conversation
from claia.core.deployments.dummy import DummyDeploymentPlugin
from claia.core.enums.conversation import MessageRole
from claia.core.modality import iter_text
from claia.core.models.dummy import DummyModel

MODULE = DummyModel


def drain(generator):
  """Collect yielded chunks and the generator's return value."""
  chunks = []
  try:
    print("\nDraining generator...\n")
    while True:
      chunk = next(generator)
      print(chunk, end="", flush=True)
      chunks.append(chunk)
  except StopIteration as stop:
    print("\nGenerator drained.\n\n")
    return chunks, stop.value


def run_model():
  """Construct DummyModel directly and stream a response."""
  model = MODULE(model_name="dummy-model")
  conversation = Conversation(title="sanity-models")
  conversation.add_message(MessageRole.USER, "Tell me a story.")
  message_count_before = len(conversation.messages)

  print(f"model: {model.model_name} ({type(model).__name__})")
  print(f"story length: {model.story_length} chars")
  print()

  # Large chunk size keeps the run snappy (DummyModel sleeps per chunk).
  # Drop chars_per_chunk / chars_per_second to watch streaming.
  chunks, full = drain(model.generate(
    conversation,
  ))

  preview = "".join(chunks)[:120].replace("\n", " ")
  print(f"chunks: {len(chunks)}")
  print(f"yielded chars: {sum(len(c) for c in chunks)}")
  print(f"return chars: {len(full) if full else 0}")
  print(f"preview: {preview}...")
  print(f"conversation untouched: {len(conversation.messages) == message_count_before}")
  print()


def run_deployment():
  """Same path through DummyDeploymentPlugin (model_class + cache)."""
  deployment = DummyDeploymentPlugin()
  info = deployment.get_deployment_info()
  conversation = Conversation(title="sanity-models-deploy")
  conversation.add_message(MessageRole.USER, "Tell me a story.")

  print(f"deployment: {info.name} - {info.description}")

  chunks = list(iter_text(deployment.run(
    model_name="dummy-model",
    model_class=MODULE,
    conversation=conversation,
    cache={},
    init_kwargs={},
    runtime_kwargs={"chars_per_second": 1_000_000, "chars_per_chunk": 10_000},
  )))

  preview = "".join(chunks)[:120].replace("\n", " ")
  print(f"chunks: {len(chunks)}")
  print(f"yielded chars: {sum(len(c) for c in chunks)}")
  print(f"preview: {preview}...")
  print()


if __name__ == "__main__":
  print("Starting...")
  run_model()
  run_deployment()
