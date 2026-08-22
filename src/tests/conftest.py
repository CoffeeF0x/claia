"""
Shared pytest fixtures for CLAIA tests.
"""

# External dependencies
import pytest

# Internal dependencies
from claia.core.results import Result, DeploymentError
from claia.core.data import Conversation
from claia.core.data.chunks import TextChunk
from claia.core.data.response import ModelResponse
from claia.core.definitions.model_definition import ModelDefinition
from claia.core.deployments.base import BaseDeployment
from claia.core.nodes.local import LocalNode
from claia.core.plugins.base import ArchitectureInfo, DeploymentInfo
from claia.framework.task import Task


# ---------------------------------------------------------------------------
# Core test fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def conversation(tmp_path):
  """Provide a minimal in-memory Conversation object."""
  return Conversation(title="Test Conversation")


@pytest.fixture
def task(conversation):
  """Provide a Task with a dummy model_id and the conversation."""
  return Task(conversation=conversation, parameters={"model_id": "dummy-model"})


@pytest.fixture
def fake_model_registry_ok():
  """A minimal registry whose run() yields tokens (streaming) or returns Result."""
  class FakeRegistry:
    def run(self, model_id, conversation, streaming=False, **kwargs):
      if streaming:
        return iter([TextChunk(data=f'{{"echo_model": "{model_id}"}}')])
      return Result.ok(f'{{"echo_model": "{model_id}"}}')

    def get_supported_models(self):
      return {}

    def resolve_qualified_name(self, name):
      return name
  return FakeRegistry()


@pytest.fixture
def fake_model_registry_error():
  """A minimal registry whose run() raises (streaming) or returns error Result."""
  class FakeRegistry:
    def run(self, model_id, conversation, streaming=False, **kwargs):
      if streaming:
        raise DeploymentError("model error")
      return Result.fail("model error")

    def get_supported_models(self):
      return {}

    def resolve_qualified_name(self, name):
      return name
  return FakeRegistry()


# ---------------------------------------------------------------------------
# Fake ModuleManager for ModelRegistry-focused tests
# ---------------------------------------------------------------------------
@pytest.fixture
def fake_manager():
  """Provide a fake Manager with just enough surface for Registry.run().

  Uses the real ``LocalNode`` and ``BaseDeployment`` relay so tests
  exercise the actual serving path: solve -> node -> deployment ->
  architecture.
  """
  class FakeArchitecture:
    deployment = "api"
    info = ArchitectureInfo(
      name="dummy_arch",
      title="Dummy Architecture",
      description="Test architecture",
    )

    def __init__(self, model_name):
      self.model_name = model_name

    def generate(self, inputs, **kwargs):
      yield TextChunk(data=f"deployed {self.model_name} via api")
      return ModelResponse(complete=True)

  class FakeDeployment(BaseDeployment):
    info = DeploymentInfo(
      name="api",
      title="API",
      description="Test deployment",
    )
    api = True

  fake_deployment = FakeDeployment()
  node = LocalNode()

  class FakeManager:
    def discover_plugins(self):
      return None

    def load_all_plugins(self, **kwargs):
      return None

    def get_supported_models(self):
      return {
        "dummy": ModelDefinition(
          aliases=["alias1"],
          architectures=["dummy_arch"],
        )
      }

    def get_available_deployments(self):
      return {"api": fake_deployment.info}

    def get_architecture_class(self, architecture_name):
      return FakeArchitecture if architecture_name == "dummy_arch" else None

    def get_deployment_plugin(self, deployment_name):
      return fake_deployment if deployment_name == "api" else None

    def iter_node_instances(self):
      yield node

  return FakeManager()


@pytest.fixture
def fake_manager_unknown_model():
  """A fake manager with no model definitions, to exercise resolve failures."""
  class FM:
    def discover_plugins(self):
      return None
    def load_all_plugins(self, **kwargs):
      return None
    def get_supported_models(self):
      return {}
    def get_available_deployments(self):
      return {}
    def iter_node_instances(self):
      return iter(())
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
    resolve_runtime_kwargs = staticmethod(RealManager.resolve_runtime_kwargs)
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
def registry_with_unknown_model(fake_manager_unknown_model, monkeypatch):
  """Unified Registry instance whose manager has no resolvable models."""
  import claia.framework.registry as regmod
  monkeypatch.setattr(regmod, "Manager", _make_fake_manager_class(fake_manager_unknown_model))
  from claia.framework.registry import Registry
  return Registry()
