# Tests for SimpleAgent

# External dependencies
import pytest

# Internal dependencies
from claia.agents.simple import SimpleAgent
from claia.lib.enums.process import ProcessStatus


def test_simple_agent_success(process, fake_model_registry_ok):
  updated = SimpleAgent.process_request(process, registry=fake_model_registry_ok)
  assert updated.status == ProcessStatus.COMPLETED
  assert isinstance(updated.result, str)
  assert updated.error is None


def test_simple_agent_emits_token_callbacks(process, fake_model_registry_ok):
  tokens = []
  process.on("token", lambda t: tokens.append(t))
  updated = SimpleAgent.process_request(process, registry=fake_model_registry_ok)
  assert updated.status == ProcessStatus.COMPLETED
  assert len(tokens) > 0


def test_simple_agent_error(process, fake_model_registry_error):
  updated = SimpleAgent.process_request(process, registry=fake_model_registry_error)
  assert updated.status == ProcessStatus.FAILED
  assert updated.result is None
  assert isinstance(updated.error, str)
  assert "model error" in updated.error
