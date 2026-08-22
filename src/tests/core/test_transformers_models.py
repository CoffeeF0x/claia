"""
Tests for local Hugging Face transformers model behavior.
"""

import importlib
import sys
import types
from queue import Queue

from claia.core.data import Conversation
from claia.core.enums.conversation import MessageRole


class FakeNoGrad:
  def __enter__(self):
    return None

  def __exit__(self, exc_type, exc, traceback):
    return False


class FakeTensor:
  def __init__(self, tokens):
    self.tokens = tokens
    self.shape = (1, len(tokens))

  def to(self, device):
    return self

  def __getitem__(self, item):
    return self.tokens[item]


class FakeTokenizer:
  eos_token = "<eos>"
  eos_token_id = 0
  pad_token = None

  def __call__(self, prompt, return_tensors=None, padding=False, truncation=False):
    return {"input_ids": FakeTensor([1, 2, 3])}

  def decode(self, tokens, skip_special_tokens=True):
    return "blocked response"


class FakeStreamer:
  def __init__(self, tokenizer, skip_prompt=False, skip_special_tokens=False, timeout=None):
    self.text_queue = Queue()
    self.stop_signal = object()
    self.timeout = timeout

  def on_finalized_text(self, text, stream_end=False):
    if text:
      self.text_queue.put(text)
    if stream_end:
      self.text_queue.put(self.stop_signal)

  def __iter__(self):
    return self

  def __next__(self):
    item = self.text_queue.get(timeout=self.timeout)
    if item is self.stop_signal:
      raise StopIteration
    return item


class FakeModel:
  def __init__(self):
    self.calls = []

  def generate(self, **kwargs):
    self.calls.append(kwargs)
    streamer = kwargs.get("streamer")
    if streamer:
      streamer.on_finalized_text("hello ")
      streamer.on_finalized_text("world", stream_end=True)
      return None
    return [FakeTensor([1, 2, 3, 4, 5])]


def _import_generic_module(monkeypatch):
  fake_transformers = types.SimpleNamespace(
    AutoTokenizer=object(),
    AutoModelForCausalLM=object(),
    TextIteratorStreamer=FakeStreamer,
  )
  fake_torch = types.SimpleNamespace(
    no_grad=lambda: FakeNoGrad(),
    float16="float16",
    float32="float32",
  )
  monkeypatch.setitem(sys.modules, "transformers", fake_transformers)
  monkeypatch.setitem(sys.modules, "torch", fake_torch)
  monkeypatch.delitem(sys.modules, "claia.core.models.transformers.generic", raising=False)
  return importlib.import_module("claia.core.models.transformers.generic")


def _model(monkeypatch):
  generic = _import_generic_module(monkeypatch)
  model = generic.GenericTransformerModel("fake-model", None, defer_loading=True)
  model.loaded = True
  model.tokenizer = FakeTokenizer()
  model.model = FakeModel()
  return model


def _sequence(conversation):
  from claia.core.definitions.model_definition import ModelDefinition
  from claia.core.data.models.conversation.message_sequence import MessageSequence
  from claia.core.enums.data import ArtifactType
  return conversation.to_model_inputs(
    ModelDefinition(inputs=[ArtifactType.TEXT, MessageSequence]),
  )



def _conversation():
  conversation = Conversation(title="T")
  conversation.add_message(MessageRole.USER, "Say hi")
  return conversation


def test_generic_transformer_streams_text_deltas(monkeypatch):
  model = _model(monkeypatch)

  chunks = list(model.generate(
    _sequence(_conversation()),
    stream=True,
    max_tokens=10,
  ))

  assert [c.data for c in chunks] == ["hello ", "world"]


def test_generic_transformer_omits_unset_top_k(monkeypatch):
  model = _model(monkeypatch)

  chunks = list(model.generate(
    _sequence(_conversation()),
    stream=False,
    top_k=None,
  ))

  assert [c.data for c in chunks] == ["blocked response"]
  assert "top_k" not in model.model.calls[0]
