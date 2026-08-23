# Tests for SimpleAgent

# External dependencies
import base64

import pytest

# Internal dependencies
from claia.framework.agents.simple import SimpleAgent
from claia.core.data.chunks import AudioChunk, ImageChunk, TextChunk
from claia.core.enums.data import AudioFormat, ImageFormat
from claia.core.enums.task import TaskEvent, TaskStatus


PNG_BYTES = base64.b64decode(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)
AUDIO_BYTES = b"fake wav bytes"


def test_simple_agent_success(task, fake_model_registry_ok):
  updated = SimpleAgent.execute(task, registry=fake_model_registry_ok)
  assert updated.status == TaskStatus.COMPLETED
  assert isinstance(updated.result, str)
  assert updated.error is None


def test_simple_agent_emits_chunk_callbacks(task, fake_model_registry_ok):
  chunks = []
  task.on(TaskEvent.CHUNK, lambda c: chunks.append(c))
  updated = SimpleAgent.execute(task, registry=fake_model_registry_ok)
  assert updated.status == TaskStatus.COMPLETED
  assert len(chunks) > 0
  assert all(isinstance(c, TextChunk) for c in chunks)


def test_simple_agent_error(task, fake_model_registry_error):
  updated = SimpleAgent.execute(task, registry=fake_model_registry_error)
  assert updated.status == TaskStatus.FAILED
  assert updated.result is None
  assert isinstance(updated.error, str)
  assert "model error" in updated.error


def test_simple_agent_attaches_image_artifacts(task):
  class FakeRegistry:
    def get_supported_models(self):
      return {}

    def list_tools(self):
      return []

    def resolve_qualified_name(self, name):
      return name

    def run(self, model_id, conversation, streaming=False, **kwargs):
      assert streaming is True
      return iter([
        TextChunk(data="Generated image."),
        ImageChunk(
          data=PNG_BYTES,
          format=ImageFormat.PNG,
          metadata={
            "media_type": "image/png",
            "format": "PNG",
            "index": 0,
            "prompt": "fox",
          },
        ),
      ])

  artifacts = []
  task.on(TaskEvent.ARTIFACT, lambda artifact, message_id: artifacts.append((artifact, message_id)))

  updated = SimpleAgent.execute(task, registry=FakeRegistry())

  assert updated.status == TaskStatus.COMPLETED
  assistant_message = updated.conversation.get_latest_message()
  assert assistant_message.content == "Generated image."
  assert len(artifacts) == 1
  artifact, message_id = artifacts[0]
  assert message_id == assistant_message.message_id
  assert artifact in assistant_message.artifacts
  assert artifact.load_bytes() == PNG_BYTES


def test_simple_agent_attaches_audio_artifacts(task):
  class FakeRegistry:
    def get_supported_models(self):
      return {}

    def list_tools(self):
      return []

    def resolve_qualified_name(self, name):
      return name

    def run(self, model_id, conversation, streaming=False, **kwargs):
      assert streaming is True
      return iter([
        TextChunk(data="Generated audio."),
        AudioChunk(
          data=AUDIO_BYTES,
          format=AudioFormat.WAV,
          metadata={
            "media_type": "audio/wav",
            "format": "WAV",
            "sample_rate": 22050,
            "prompt": "fox",
          },
        ),
      ])

  artifacts = []
  task.on(TaskEvent.ARTIFACT, lambda artifact, message_id: artifacts.append((artifact, message_id)))

  updated = SimpleAgent.execute(task, registry=FakeRegistry())

  assert updated.status == TaskStatus.COMPLETED
  assistant_message = updated.conversation.get_latest_message()
  assert assistant_message.content == "Generated audio."
  assert any(a.id == artifacts[0][0].id for a in assistant_message.artifacts)
  assert len(artifacts) == 1
  artifact, message_id = artifacts[0]
  assert message_id == assistant_message.message_id
  assert artifact in assistant_message.artifacts
  assert artifact.load_content() == AUDIO_BYTES
