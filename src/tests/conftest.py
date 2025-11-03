"""
Shared pytest fixtures for CLAIA tests.
"""

# External dependencies
import pytest
from types import SimpleNamespace

# Internal dependencies
from claia.lib.results import Result
from claia.lib.data import Conversation
from claia.lib.process import Process
from claia.lib.enums.process import ProcessStatus


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
  """A minimal registry whose run() returns success."""
  class FakeRegistry:
    def run(self, model_id, conversation, **kwargs):
      return Result.ok({"echo_model": model_id})
  return FakeRegistry()


@pytest.fixture
def fake_model_registry_error():
  """A minimal registry whose run() returns an error."""
  class FakeRegistry:
    def run(self, model_id, conversation, **kwargs):
      return Result.fail("model error")
  return FakeRegistry()


# ---------------------------------------------------------------------------
# Fake ModuleManager for ModelRegistry-focused tests
# ---------------------------------------------------------------------------
@pytest.fixture
def fake_manager():
  """Provide a fake ModuleManager with just enough surface for ModelRegistry.run()."""
  class FakeManager:
    def load_all_plugins(self):
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
            required_args = []
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
            required_args = []
          return Info()

        def run(self, model_name, model_class, conversation, cache, **kwargs):
          return Result.ok(f"deployed {model_name} via {deployment_name}")
      return Deployment()

    def get_available_architectures(self):
      class ArchInfo:
        required_args = []
      return {"dummy_arch": ArchInfo()}

  return FakeManager()


@pytest.fixture
def fake_manager_no_solver():
  """A fake manager that returns no solver, to exercise error handling path."""
  class FM:
    def load_all_plugins(self):
      return None
    def get_supported_models(self):
      return {}
    def get_available_deployments(self):
      return {}
    def get_solver_plugin(self, solver_name=None):
      return None
  return FM()


@pytest.fixture
def registry_with_fake_manager(fake_manager, monkeypatch):
  """Unified Registry instance wired to the fake manager via monkeypatching."""
  import claia.registry as regmod
  # Ensure Registry.__init__ uses our fake manager
  monkeypatch.setattr(regmod, "Manager", lambda: fake_manager)
  from claia.registry import Registry
  return Registry()


@pytest.fixture
def registry_with_no_solver(fake_manager_no_solver, monkeypatch):
  """Unified Registry instance whose manager returns no solver plugin."""
  import claia.registry as regmod
  monkeypatch.setattr(regmod, "Manager", lambda: fake_manager_no_solver)
  from claia.registry import Registry
  return Registry()
