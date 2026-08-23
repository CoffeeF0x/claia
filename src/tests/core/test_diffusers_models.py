"""
Tests for local Hugging Face Diffusers image model behavior.
"""

import importlib
import sys
import types

from claia.core.data import AgentRequest, Conversation
from claia.core.data.chunks import ImageChunk, TextChunk
from claia.core.data.response import ModelResponse
from claia.core.deployments.transformers import TransformersDeployment
from claia.core.enums.conversation import MessageRole
from claia.core.enums.data import ImageFormat


class FakeGenerator:
  def __init__(self, device=None):
    self.device = device
    self.seed = None

  def manual_seed(self, seed):
    self.seed = seed
    return self


class FakeImage:
  width = 64
  height = 32
  mode = "RGB"

  def save(self, buffer, format=None):
    buffer.write(f"{format}:fake-image".encode())


class FakePipeline:
  loaded = []

  def __init__(self):
    self.device = None
    self.calls = []
    self.saved_to = None

  @classmethod
  def from_pretrained(cls, model_name, **kwargs):
    pipeline = cls()
    pipeline.loaded_from = model_name
    pipeline.load_kwargs = kwargs
    cls.loaded.append(pipeline)
    return pipeline

  def to(self, device):
    self.device = device
    return self

  def __call__(self, **kwargs):
    self.calls.append(kwargs)
    return types.SimpleNamespace(images=[FakeImage()])

  def save_pretrained(self, model_path):
    self.saved_to = model_path


def _import_diffusers_module(monkeypatch):
  fake_transformers = types.SimpleNamespace(
    AutoTokenizer=object(),
    AutoModelForCausalLM=object(),
    TextIteratorStreamer=object(),
  )
  fake_torch = types.SimpleNamespace(
    Generator=FakeGenerator,
    cuda=types.SimpleNamespace(is_available=lambda: False),
    float16="float16",
    float32="float32",
  )
  fake_diffusers = types.SimpleNamespace(DiffusionPipeline=FakePipeline)

  monkeypatch.setitem(sys.modules, "transformers", fake_transformers)
  monkeypatch.setitem(sys.modules, "torch", fake_torch)
  monkeypatch.setitem(sys.modules, "diffusers", fake_diffusers)
  monkeypatch.delitem(sys.modules, "claia.core.architectures.transformers.diffusers", raising=False)
  FakePipeline.loaded = []
  return importlib.import_module("claia.core.architectures.transformers.diffusers")


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
  conversation.add_message(MessageRole.USER, "A small fox in a library")
  return conversation


def test_diffusers_model_yields_text_and_image_chunks(monkeypatch):
  diffusers = _import_diffusers_module(monkeypatch)
  model = diffusers.DiffusersArchitecture(
    "sd2-community/stable-diffusion-2",
    defer_loading=True,
    huggingface_api_token="hf_test",
  )

  chunks = list(model.generate(_request(
    _artifacts(_conversation()),
    height=32,
    width=64,
    num_inference_steps=7,
    guidance_scale=6.5,
    negative_prompt="blurry",
    seed=123,
    num_images=1,
    output_format="png",
  )))

  assert isinstance(chunks[0], TextChunk)
  assert chunks[0].data == "Generated 1 image."
  assert isinstance(chunks[1], ImageChunk)
  assert chunks[1].data == b"PNG:fake-image"
  assert chunks[1].metadata["media_type"] == "image/png"
  assert chunks[1].metadata["model"] == "sd2-community/stable-diffusion-2"
  assert chunks[1].metadata["prompt"] == "A small fox in a library"
  assert chunks[1].metadata["seed"] == 123

  pipeline = FakePipeline.loaded[0]
  assert pipeline.loaded_from == "sd2-community/stable-diffusion-2"
  assert pipeline.load_kwargs["token"] == "hf_test"
  assert pipeline.device == "cpu"
  assert pipeline.calls[0]["prompt"] == "A small fox in a library"
  assert pipeline.calls[0]["height"] == 32
  assert pipeline.calls[0]["width"] == 64
  assert pipeline.calls[0]["num_inference_steps"] == 7
  assert pipeline.calls[0]["guidance_scale"] == 6.5
  assert pipeline.calls[0]["negative_prompt"] == "blurry"
  assert pipeline.calls[0]["num_images_per_prompt"] == 1
  assert pipeline.calls[0]["generator"].seed == 123


def test_diffusers_model_allows_prompt_override(monkeypatch):
  diffusers = _import_diffusers_module(monkeypatch)
  model = diffusers.DiffusersArchitecture("example/image-model", defer_loading=True)

  chunks = list(model.generate(_request(
    _artifacts(_conversation()),
    prompt="Override prompt",
  )))

  assert chunks[1].metadata["prompt"] == "Override prompt"
  assert FakePipeline.loaded[0].calls[0]["prompt"] == "Override prompt"


def test_transformers_deployment_passes_image_chunks_through():
  image_chunk = ImageChunk(
    data=b"image",
    format=ImageFormat.PNG,
    metadata={"media_type": "image/png"},
  )

  class ImageArchitecture:
    def __init__(self, model_name, model_path=None, defer_loading=False, device="cpu"):
      self.model_name = model_name

    def generate(self, request):
      yield image_chunk
      return ModelResponse(chunks=[image_chunk], complete=True)

  deployment = TransformersDeployment()
  request = AgentRequest(
    model="fake-image-model",
    provider_model="fake-image-model",
    architecture_class=ImageArchitecture,
    deployment=deployment,
    inputs=_artifacts(_conversation()),
  )
  instance = deployment.deploy(request)
  chunks = list(deployment.run(instance, request))

  assert len(chunks) == 1
  assert isinstance(chunks[0], ImageChunk)
  assert chunks[0].data == b"image"
