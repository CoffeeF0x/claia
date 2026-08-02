# Tests for SimpleAgent

# External dependencies
import base64

import pytest

# Internal dependencies
from claia.framework.agents.simple import SimpleAgent
from claia.core.data.chunks import AudioChunk, ImageChunk, TextChunk
from claia.core.enums.data import AudioFormat, ImageFormat
from claia.core.enums.process import ProcessStatus


PNG_BYTES = base64.b64decode(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)
AUDIO_BYTES = b"fake wav bytes"


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


def test_simple_agent_attaches_image_artifacts(process):
  class FakeRegistry:
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
  process.on("artifact", lambda artifact, message_id: artifacts.append((artifact, message_id)))

  updated = SimpleAgent.process_request(process, registry=FakeRegistry())

  assert updated.status == ProcessStatus.COMPLETED
  assistant_message = updated.conversation.get_latest_message()
  assert assistant_message.content == "Generated image."
  assert len(artifacts) == 1
  artifact, message_id = artifacts[0]
  assert message_id == assistant_message.message_id
  assert artifact in assistant_message.artifacts
  assert artifact.load_bytes() == PNG_BYTES


def test_simple_agent_attaches_audio_artifacts(process):
  class FakeRegistry:
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
  process.on("artifact", lambda artifact, message_id: artifacts.append((artifact, message_id)))

  updated = SimpleAgent.process_request(process, registry=FakeRegistry())

  assert updated.status == ProcessStatus.COMPLETED
  assistant_message = updated.conversation.get_latest_message()
  assert assistant_message.content == "Generated audio."
  assert any(a.id == artifacts[0][0].id for a in assistant_message.artifacts)
  assert len(artifacts) == 1
  artifact, message_id = artifacts[0]
  assert message_id == assistant_message.message_id
  assert artifact in assistant_message.artifacts
  assert artifact.load_content() == AUDIO_BYTES
