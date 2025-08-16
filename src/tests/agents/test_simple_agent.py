# Tests for SimpleAgent

# External dependencies
import pytest

# Internal dependencies
from claia.agents.builtin.simple import SimpleAgent
from claia.common.enums.agent import ProcessStatus


def test_simple_agent_success(process, fake_model_registry_ok):
  updated = SimpleAgent.process_request(process, model_registry=fake_model_registry_ok)
  assert updated.status == ProcessStatus.COMPLETED
  assert isinstance(updated.result, dict)
  assert updated.result.get("echo_model") == process.parameters["model_id"]
  assert updated.error is None


def test_simple_agent_error(process, fake_model_registry_error):
  updated = SimpleAgent.process_request(process, model_registry=fake_model_registry_error)
  assert updated.status == ProcessStatus.FAILED
  assert updated.result is None
  assert isinstance(updated.error, str)
  assert "Error running model: model error" in updated.error
