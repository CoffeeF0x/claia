# Tests for unified Registry (model APIs) using a fake manager via monkeypatch

# External dependencies
import pytest

# Internal dependencies
from claia.framework.registry import Registry
from claia.core.results import ResolveError
from claia.core.data import Conversation
from claia.core.data.response import AgentResponse


def test_model_registry_run_success(registry_with_fake_manager, tmp_path):
  conv = Conversation(title="T")
  reg: Registry = registry_with_fake_manager
  res = reg.run("dummy", conv)
  assert isinstance(res, AgentResponse)
  assert res.is_success()
  assert isinstance(res.text(), str)
  assert "deployed dummy via api" in res.text()
  assert res.metrics is not None


def test_model_registry_run_streaming_yields_generation_chunks(registry_with_fake_manager, tmp_path):
  """registry.run(streaming=True) exposes the BaseChunk stream."""
  from claia.core.data.chunks import MetricsChunk, TextChunk
  conv = Conversation(title="T")
  reg: Registry = registry_with_fake_manager
  response = reg.run("dummy", conv, streaming=True)
  chunks = list(response)
  assert len(chunks) > 0
  assert any(isinstance(c, TextChunk) for c in chunks)
  assert any(isinstance(c, MetricsChunk) for c in chunks)
  assert response.metrics is not None


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
  with pytest.raises(ResolveError, match="not found"):
    reg.run("dummy", conv)


def test_query_unblocks_on_cancel(registry_with_fake_manager):
  reg: Registry = registry_with_fake_manager

  def cancel_immediately(task):
    task.mark_cancelled()
    return task.id

  reg.add_task = cancel_immediately
  result = reg.query("dummy", "hello")
  assert result.is_error()
  assert result.get_message() == "cancelled"


def test_model_registry_unknown_model_streaming_raises(registry_with_unknown_model, tmp_path):
  conv = Conversation(title="T")
  reg: Registry = registry_with_unknown_model
  with pytest.raises(ResolveError, match="not found"):
    for _ in reg.run("dummy", conv, streaming=True):
      pass


def _make_identifier_manager(claia_name, architecture_name, provider_name):
  """Fake manager serving one weight-holding model through the real node path."""
  from claia.core.data.chunks import TextChunk
  from claia.core.definitions.model_definition import ModelDefinition
  from claia.core.deployments.base import BaseDeployment
  from claia.core.nodes.local import LocalNode
  from claia.core.plugins.base import ArchitectureInfo, DeploymentInfo
  from claia.framework.manager import Manager as RealManager

  class EchoArchitecture:
    deployment = "transformers"
    info = ArchitectureInfo(
      name=architecture_name,
      title=architecture_name,
      description="Test architecture",
    )

    def __init__(self, model_name, model_path=None, defer_loading=False, device="cpu"):
      self.model_name = model_name

    def generate(self, request):
      yield TextChunk(data=self.model_name)

  class FakeDeployment(BaseDeployment):
    info = DeploymentInfo(
      name="transformers",
      title="Transformers",
      description="Test deployment",
    )

  fake_deployment = FakeDeployment()
  node = LocalNode()

  class FakeManager:
    # Registry reaches for kwarg-shaping statics on the module-level
    # ``Manager`` symbol; delegate those to the real class.
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
        claia_name: ModelDefinition(
          architectures=[architecture_name],
          identifiers={architecture_name: provider_name},
        )
      }

    def get_available_deployments(self):
      return {"transformers": fake_deployment.info}

    def get_architecture_class(self, name):
      return EchoArchitecture if name == architecture_name else None

    def get_deployment_plugin(self, name):
      return fake_deployment if name == "transformers" else None

    def iter_node_instances(self):
      yield node

  return FakeManager


def test_model_registry_resolves_diffusers_provider_identifier(monkeypatch):
  """Stable Diffusion resolves from Claia id to provider id before serving."""
  import claia.framework.registry as registry_module

  monkeypatch.setattr(registry_module, "Manager", _make_identifier_manager(
    "stable-diffusion-v2", "diffusers", "sd2-community/stable-diffusion-2",
  ))

  reg = Registry()
  result = reg.run("stable-diffusion-v2", Conversation(title="T"))

  assert result.is_success()
  assert result.text() == "sd2-community/stable-diffusion-2"


def test_model_registry_resolves_tts_provider_identifier(monkeypatch):
  """Qwen TTS resolves from Claia id to provider id before serving."""
  import claia.framework.registry as registry_module

  monkeypatch.setattr(registry_module, "Manager", _make_identifier_manager(
    "qwen3-tts-0.6b", "tts", "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
  ))

  reg = Registry()
  result = reg.run("qwen3-tts-0.6b", Conversation(title="T"))

  assert result.is_success()
  assert result.text() == "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
