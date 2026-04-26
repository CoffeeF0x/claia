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
  """registry.run(streaming=True) exposes the chunk stream as promised by Phase 4."""
  from claia.core.modality import ChunkKind, GenerationChunk
  conv = Conversation(title="T")
  reg: Registry = registry_with_fake_manager
  chunks = list(reg.run("dummy", conv, streaming=True))
  assert len(chunks) > 0
  assert all(isinstance(c, GenerationChunk) for c in chunks)
  assert all(c.kind is ChunkKind.TEXT for c in chunks)


def test_model_registry_stream_text_flattens_to_strings(registry_with_fake_manager, tmp_path):
  """The stream_text convenience yields plain strings from TEXT chunks."""
  conv = Conversation(title="T")
  reg: Registry = registry_with_fake_manager
  tokens = list(reg.stream_text("dummy", conv))
  assert len(tokens) > 0
  assert all(isinstance(t, str) for t in tokens)
  assert any("deployed dummy via api" in t for t in tokens)


def test_model_registry_no_solver(registry_with_no_solver, tmp_path):
  conv = Conversation(title="T")
  reg: Registry = registry_with_no_solver
  res: Result = reg.run("dummy", conv)
  assert res.is_error()
  assert "No solver available" in res.get_message()


def test_model_registry_no_solver_streaming_raises(registry_with_no_solver, tmp_path):
  conv = Conversation(title="T")
  reg: Registry = registry_with_no_solver
  with pytest.raises(DeploymentError, match="No solver available"):
    for _ in reg.run("dummy", conv, streaming=True):
      pass


def test_model_registry_resolves_diffusers_provider_identifier(monkeypatch):
  """Stable Diffusion resolves from Claia id to provider id before deployment."""
  from claia.core.definitions.model_definition import ModelDefinition
  from claia.core.plugins.base import ArchitectureInfo, DeploymentInfo
  from claia.core.solvers.default import DefaultSolverPlugin
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

    def get_solver_plugin(self, solver_name=None):
      return DefaultSolverPlugin()

    def get_model_class(self, architecture_name):
      class DummyModel:
        pass
      return DummyModel

    def get_deployment_plugin(self, deployment_name):
      class Deployment:
        def get_deployment_info(self):
          return DeploymentInfo(
            name="local",
            title="Local",
            description="Local test deployment",
          )

        def run(self, model_name, model_class, conversation, cache, init_kwargs, runtime_kwargs):
          from claia.core.modality import text_chunk
          yield text_chunk(model_name)

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
