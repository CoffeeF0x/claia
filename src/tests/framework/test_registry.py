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
