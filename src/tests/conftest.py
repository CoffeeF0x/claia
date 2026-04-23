"""
Shared pytest fixtures for CLAIA tests.
"""

# External dependencies
import pytest
from types import SimpleNamespace

# Internal dependencies
from claia.core.results import Result, DeploymentError
from claia.core.data import Conversation
from claia.core.modality import GenerationChunk, text_chunk
from claia.framework.process import Process
from claia.core.enums.process import ProcessStatus


# ---------------------------------------------------------------------------
# Core test fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def conversation(tmp_path):
  """Provide a minimal in-memory Conversation object."""
  return Conversation(title="Test Conversation")


@pytest.fixture
def process(conversation):
  """Provide a Process with a dummy model_id and the conversation."""
  return Process(conversation=conversation, parameters={"model_id": "dummy-model"})


@pytest.fixture
def fake_model_registry_ok():
  """A minimal registry whose run() yields tokens (streaming) or returns Result."""
  class FakeRegistry:
    def run(self, model_id, conversation, streaming=False, **kwargs):
      if streaming:
        return iter([text_chunk(f'{{"echo_model": "{model_id}"}}')])
      return Result.ok(f'{{"echo_model": "{model_id}"}}')
  return FakeRegistry()


@pytest.fixture
def fake_model_registry_error():
  """A minimal registry whose run() raises (streaming) or returns error Result."""
  class FakeRegistry:
    def run(self, model_id, conversation, streaming=False, **kwargs):
      if streaming:
        raise DeploymentError("model error")
      return Result.fail("model error")
  return FakeRegistry()


# ---------------------------------------------------------------------------
# Fake ModuleManager for ModelRegistry-focused tests
# ---------------------------------------------------------------------------
@pytest.fixture
def fake_manager():
  """Provide a fake ModuleManager with just enough surface for ModelRegistry.run()."""
  class FakeManager:
    def discover_plugins(self):
      return None

    def load_all_plugins(self, **kwargs):
      return None

    def get_supported_models(self):
      return {"dummy": {"aliases": ["alias1"]}}

    def get_available_deployments(self):
      return {"api": object()}

    def get_solver_plugin(self, solver_name=None):
      class Solver:
        def get_solver_info(self):
          class Info:
            name = "default"
            params = []
          return Info()

        def solve_deployment(self, model_name, available_deployments, available_models, cache, deployment_preference=None, deployment_method=None, **kwargs):
          return Result.ok(SimpleNamespace(
            deployment_name="api",
            model_name=model_name,
            architecture_name="dummy_arch"
          ))
      return Solver()

    def get_model_class(self, architecture_name):
      class DummyModel:
        pass
      return DummyModel

    def get_deployment_plugin(self, deployment_name):
      class Deployment:
        def get_deployment_info(self):
          class Info:
            name = "api"
            params = []
          return Info()

        def run(self, model_name, model_class, conversation, cache, **kwargs):
          yield text_chunk(f"deployed {model_name} via {deployment_name}")
      return Deployment()

    def get_available_architectures(self):
      class ArchInfo:
        params = []
      return {"dummy_arch": ArchInfo()}

  return FakeManager()


@pytest.fixture
def fake_manager_no_solver():
  """A fake manager that returns no solver, to exercise error handling path."""
  class FM:
    def discover_plugins(self):
      return None
    def load_all_plugins(self, **kwargs):
      return None
    def get_supported_models(self):
      return {}
    def get_available_deployments(self):
      return {}
    def get_solver_plugin(self, solver_name=None):
      return None
  return FM()


def _make_fake_manager_class(fake_manager):
  """
  Wrap ``fake_manager`` in a thin class so ``regmod.Manager`` still
  resolves to a class (not a bare callable). This matters because the
  Registry reaches for class-level static methods on ``Manager`` (e.g.
  ``Manager.filter_init_kwargs``) at dispatch time; a plain lambda
  wouldn't expose those.
  """
  from claia.framework.manager import Manager as RealManager

  class _FakeManagerFactory:
    # Delegate kwarg-shaping statics to the real Manager so dispatch
    # still performs spec-aware filtering and validation under test.
    coerce_value = staticmethod(RealManager.coerce_value)
    filter_init_kwargs = staticmethod(RealManager.filter_init_kwargs)
    filter_runtime_kwargs = staticmethod(RealManager.filter_runtime_kwargs)
    validate_required_init_kwargs = staticmethod(RealManager.validate_required_init_kwargs)
    _COERCE_FAIL = RealManager._COERCE_FAIL
    _mask_for_log = staticmethod(RealManager._mask_for_log)

    def __new__(cls):
      return fake_manager

  return _FakeManagerFactory


@pytest.fixture
def registry_with_fake_manager(fake_manager, monkeypatch):
  """Unified Registry instance wired to the fake manager via monkeypatching."""
  import claia.framework.registry as regmod
  monkeypatch.setattr(regmod, "Manager", _make_fake_manager_class(fake_manager))
  from claia.framework.registry import Registry
  return Registry()


@pytest.fixture
def registry_with_no_solver(fake_manager_no_solver, monkeypatch):
  """Unified Registry instance whose manager returns no solver plugin."""
  import claia.framework.registry as regmod
  monkeypatch.setattr(regmod, "Manager", _make_fake_manager_class(fake_manager_no_solver))
  from claia.framework.registry import Registry
  return Registry()
