"""
Tests for local text-to-speech model behavior.
"""

import importlib
import sys
import types

from claia.core.data import AgentRequest, Conversation
from claia.core.data.chunks import AudioChunk, TextChunk
from claia.core.enums.conversation import MessageRole


class FakeQwen3TTSModel:
  loaded = []

  def __init__(self):
    self.calls = []

  @classmethod
  def from_pretrained(cls, model_name, **kwargs):
    model = cls()
    model.loaded_from = model_name
    model.load_kwargs = kwargs
    cls.loaded.append(model)
    return model

  def generate_voice_clone(self, text, language, ref_audio):
    self.calls.append({
      "text": text,
      "language": language,
      "ref_audio": ref_audio,
    })
    return (["fake-waveform"], 22050)


def _import_tts_module(monkeypatch):
  fake_transformers = types.SimpleNamespace(
    AutoTokenizer=object(),
    AutoModelForCausalLM=object(),
    TextIteratorStreamer=object(),
  )
  fake_torch = types.SimpleNamespace(
    float16="float16",
    float32="float32",
    bfloat16="bfloat16",
  )
  fake_qwen_tts = types.SimpleNamespace(Qwen3TTSModel=FakeQwen3TTSModel)

  def write(buffer, audio, sample_rate, format=None):
    buffer.write(f"{format}:{sample_rate}:{audio}".encode())

  fake_soundfile = types.SimpleNamespace(write=write)

  monkeypatch.setitem(sys.modules, "transformers", fake_transformers)
  monkeypatch.setitem(sys.modules, "torch", fake_torch)
  monkeypatch.setitem(sys.modules, "qwen_tts", fake_qwen_tts)
  monkeypatch.setitem(sys.modules, "soundfile", fake_soundfile)
  monkeypatch.delitem(sys.modules, "claia.core.architectures.transformers.tts", raising=False)
  FakeQwen3TTSModel.loaded = []
  return importlib.import_module("claia.core.architectures.transformers.tts")


def _request(inputs, **args):
  return AgentRequest(
    model="test",
    provider_model="test",
    architecture_class=object,
    deployment=None,
    inputs=inputs,
    args=args,
  )


def _artifacts(conversation):
  from claia.core.definitions.model_definition import ModelDefinition
  from claia.core.enums.data import ArtifactType
  return conversation.to_model_inputs(
    ModelDefinition(inputs=[ArtifactType.TEXT]),
  )



def _conversation():
  conversation = Conversation(title="T")
  conversation.add_message(MessageRole.USER, "Read this aloud.")
  return conversation


def test_local_tts_model_yields_text_and_audio_chunks(monkeypatch):
  tts = _import_tts_module(monkeypatch)
  model = tts.TTSArchitecture(
    "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
    defer_loading=True,
    device="cuda",
    dtype="bfloat16",
    huggingface_api_token="hf_test",
  )

  chunks = list(model.generate(_request(
    _artifacts(_conversation()),
    language="English",
    reference_audio_path="/tmp/ref.wav",
    response_format="wav",
  )))

  assert isinstance(chunks[0], TextChunk)
  assert chunks[0].data == "Generated audio."
  assert isinstance(chunks[1], AudioChunk)
  assert chunks[1].data == b"WAV:22050:fake-waveform"
  assert chunks[1].metadata["media_type"] == "audio/wav"
  assert chunks[1].metadata["format"] == "WAV"
  assert chunks[1].metadata["model"] == "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
  assert chunks[1].metadata["prompt"] == "Read this aloud."
  assert chunks[1].metadata["sample_rate"] == 22050

  qwen_model = FakeQwen3TTSModel.loaded[0]
  assert qwen_model.loaded_from == "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
  assert qwen_model.load_kwargs["device_map"] == "cuda:0"
  assert qwen_model.load_kwargs["dtype"] == "bfloat16"
  assert qwen_model.load_kwargs["token"] == "hf_test"
  assert qwen_model.calls[0] == {
    "text": "Read this aloud.",
    "language": "English",
    "ref_audio": "/tmp/ref.wav",
  }


def test_local_tts_model_allows_prompt_override(monkeypatch):
  tts = _import_tts_module(monkeypatch)
  model = tts.TTSArchitecture("example/tts", defer_loading=True)

  chunks = list(model.generate(_request(
    _artifacts(_conversation()),
    prompt="Override text.",
    reference_audio_path="/tmp/ref.wav",
  )))

  assert chunks[1].metadata["prompt"] == "Override text."
  assert "reference_text" not in chunks[1].metadata
  assert FakeQwen3TTSModel.loaded[0].calls[0]["text"] == "Override text."


def test_local_tts_model_raises_on_missing_qwen_reference_audio(monkeypatch):
  import pytest

  tts = _import_tts_module(monkeypatch)
  model = tts.TTSArchitecture("Qwen/Qwen3-TTS-12Hz-0.6B-Base", defer_loading=True)

  with pytest.raises(ValueError, match="reference_audio_path"):
    list(model.generate(_request(_artifacts(_conversation()))))
