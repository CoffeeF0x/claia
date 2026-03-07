# Tests for unified Registry (model APIs) using a fake manager via monkeypatch

# External dependencies
import pytest

# Internal dependencies
from claia.registry import Registry
from claia.lib.results import Result, DeploymentError
from claia.lib.data import Conversation


def test_model_registry_run_success(registry_with_fake_manager, tmp_path):
  conv = Conversation(title="T")
  reg: Registry = registry_with_fake_manager
  res: Result = reg.run("dummy", conv)
  assert res.is_success()
  assert isinstance(res.get_data(), str)
  assert "deployed dummy via api" in res.get_data()


def test_model_registry_run_streaming_yields_tokens(registry_with_fake_manager, tmp_path):
  conv = Conversation(title="T")
  reg: Registry = registry_with_fake_manager
  tokens = []
  for token in reg.run("dummy", conv, streaming=True):
    tokens.append(token)
  assert len(tokens) > 0


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
