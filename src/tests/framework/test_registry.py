# Tests for unified Registry (model APIs) using a fake manager via monkeypatch

# External dependencies
import pytest

# Internal dependencies
from claia.framework.registry import Registry
from claia.core.results import Result, DeploymentError
from claia.core.data import Conversation


def test_model_registry_run_success(registry_with_fake_manager, tmp_path):
  conv = Conversation(title="T")
  reg: Registry = registry_with_fake_manager
  res: Result = reg.run("dummy", conv)
  assert res.is_success()
  assert isinstance(res.get_data(), str)
  assert "deployed dummy via api" in res.get_data()


def test_model_registry_run_streaming_yields_generation_chunks(registry_with_fake_manager, tmp_path):
  """registry.run(streaming=True) exposes the BaseChunk stream."""
  from claia.core.data.chunks import TextChunk
  conv = Conversation(title="T")
  reg: Registry = registry_with_fake_manager
  chunks = list(reg.run("dummy", conv, streaming=True))
  assert len(chunks) > 0
  assert all(isinstance(c, TextChunk) for c in chunks)


def test_model_registry_stream_text_flattens_to_strings(registry_with_fake_manager, tmp_path):
  """The stream_text convenience yields plain strings from TEXT chunks."""
  conv = Conversation(title="T")
  reg: Registry = registry_with_fake_manager
  tokens = list(reg.stream_text("dummy", conv))
  assert len(tokens) > 0
  assert all(isinstance(t, str) for t in tokens)
  assert any("deployed dummy via api" in t for t in tokens)


def test_model_registry_unknown_model(registry_with_unknown_model, tmp_path):
  conv = Conversation(title="T")
  reg: Registry = registry_with_unknown_model
  res: Result = reg.run("dummy", conv)
  assert res.is_error()
  assert "not found" in res.get_message()


def test_query_unblocks_on_cancel(registry_with_fake_manager):
  reg: Registry = registry_with_fake_manager

  def cancel_immediately(process):
    process.mark_cancelled()
    return process.id

  reg.add_process = cancel_immediately
  result = reg.query("dummy", "hello")
  assert result.is_error()
  assert result.get_message() == "cancelled"


def test_model_registry_unknown_model_streaming_raises(registry_with_unknown_model, tmp_path):
  conv = Conversation(title="T")
  reg: Registry = registry_with_unknown_model
  with pytest.raises(DeploymentError, match="not found"):
    for _ in reg.run("dummy", conv, streaming=True):
      pass


def test_model_registry_resolves_diffusers_provider_identifier(monkeypatch):
  """Stable Diffusion resolves from Claia id to provider id before deployment."""
  from claia.core.definitions.model_definition import ModelDefinition
  from claia.core.plugins.base import ArchitectureInfo, DeploymentInfo
  from claia.framework.manager import Manager as RealManager
  import claia.framework.registry as registry_module

  class FakeManager:
    coerce_value = staticmethod(RealManager.coerce_value)
    filter_init_kwargs = staticmethod(RealManager.filter_init_kwargs)
    filter_runtime_kwargs = staticmethod(RealManager.filter_runtime_kwargs)
    resolve_runtime_kwargs = staticmethod(RealManager.resolve_runtime_kwargs)
    validate_required_init_kwargs = staticmethod(RealManager.validate_required_init_kwargs)
    _COERCE_FAIL = RealManager._COERCE_FAIL
    _mask_for_log = staticmethod(RealManager._mask_for_log)

    def discover_plugins(self):
      return None

    def load_all_plugins(self, **kwargs):
      return None

    def get_supported_models(self):
      return {
        "stable-diffusion-v2": ModelDefinition(
          deployments=["local"],
          architectures=["diffusers"],
          identifiers={"diffusers": "sd2-community/stable-diffusion-2"},
        )
      }

    def get_available_deployments(self):
      return {"local": object()}

    def get_model_class(self, architecture_name):
      class DummyModel:
        pass
      return DummyModel

    def get_deployment_plugin(self, deployment_name):
      class Deployment:
        info = DeploymentInfo(
          name="local",
          title="Local",
          description="Local test deployment",
        )

        def run(self, model_name, model_class, conversation, cache, init_kwargs, runtime_kwargs, definition=None):
          from claia.core.data.chunks import TextChunk
          yield TextChunk(data=model_name)

      return Deployment()

    def get_available_architectures(self):
      return {
        "diffusers": ArchitectureInfo(
          name="diffusers",
          title="Diffusers",
          description="Diffusers test architecture",
        )
      }

  monkeypatch.setattr(registry_module, "Manager", FakeManager)

  reg = Registry()
  result = reg.run("stable-diffusion-v2", Conversation(title="T"))

  assert result.is_success()
  assert result.get_data() == "sd2-community/stable-diffusion-2"


def test_model_registry_resolves_tts_provider_identifier(monkeypatch):
  """Qwen TTS resolves from Claia id to provider id before deployment."""
  from claia.core.definitions.model_definition import ModelDefinition
  from claia.core.plugins.base import ArchitectureInfo, DeploymentInfo
  from claia.framework.manager import Manager as RealManager
  import claia.framework.registry as registry_module

  class FakeManager:
    coerce_value = staticmethod(RealManager.coerce_value)
    filter_init_kwargs = staticmethod(RealManager.filter_init_kwargs)
    filter_runtime_kwargs = staticmethod(RealManager.filter_runtime_kwargs)
    resolve_runtime_kwargs = staticmethod(RealManager.resolve_runtime_kwargs)
    validate_required_init_kwargs = staticmethod(RealManager.validate_required_init_kwargs)
    _COERCE_FAIL = RealManager._COERCE_FAIL
    _mask_for_log = staticmethod(RealManager._mask_for_log)

    def discover_plugins(self):
      return None

    def load_all_plugins(self, **kwargs):
      return None

    def get_supported_models(self):
      return {
        "qwen3-tts-0.6b": ModelDefinition(
          deployments=["local"],
          architectures=["tts"],
          identifiers={"tts": "Qwen/Qwen3-TTS-12Hz-0.6B-Base"},
        )
      }

    def get_available_deployments(self):
      return {"local": object()}

    def get_model_class(self, architecture_name):
      class DummyModel:
        pass
      return DummyModel

    def get_deployment_plugin(self, deployment_name):
      class Deployment:
        info = DeploymentInfo(
          name="local",
          title="Local",
          description="Local test deployment",
        )

        def run(self, model_name, model_class, conversation, cache, init_kwargs, runtime_kwargs, definition=None):
          from claia.core.data.chunks import TextChunk
          yield TextChunk(data=model_name)

      return Deployment()

    def get_available_architectures(self):
      return {
        "tts": ArchitectureInfo(
          name="tts",
          title="TTS",
          description="TTS test architecture",
        )
      }

  monkeypatch.setattr(registry_module, "Manager", FakeManager)

  reg = Registry()
  result = reg.run("qwen3-tts-0.6b", Conversation(title="T"))

  assert result.is_success()
  assert result.get_data() == "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
