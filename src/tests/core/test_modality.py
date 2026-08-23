"""
Tests for the chunk / response contract.
"""

from claia.core.data.chunks import (
  AudioChunk,
  ImageChunk,
  MetricsChunk,
  TextChunk,
  UsageChunk,
)
from claia.core.data.response import AgentResponse
from claia.core.enums.data import AudioFormat, ImageFormat, MediaType, TextFormat


def test_text_chunk_defaults():
  chunk = TextChunk(data="hello")
  assert isinstance(chunk, TextChunk)
  assert chunk.type is MediaType.TEXT
  assert chunk.format is TextFormat.PLAIN
  assert chunk.data == "hello"
  assert chunk.media_type == "text/plain"


def test_image_and_audio_chunks():
  image = ImageChunk(data=b"\x89PNG", format=ImageFormat.PNG)
  audio = AudioChunk(data=b"RIFF", format=AudioFormat.WAV)
  assert image.type is MediaType.IMAGE
  assert audio.type is MediaType.AUDIO


def test_agent_response_iter_text():
  response = AgentResponse(
    chunks=[
      TextChunk(data="hello "),
      ImageChunk(data=b"..."),
      TextChunk(data="world"),
    ],
    complete=True,
  )
  assert list(response.iter_text()) == ["hello ", "world"]
  assert response.text() == "hello world"
  assert response.is_success()
  assert response.usage is None
  assert response.metrics is None


def test_agent_response_error():
  response = AgentResponse(chunks=[], complete=False, error="boom")
  assert not response.is_success()


def test_agent_response_usage_and_metrics():
  usage = UsageChunk(prompt_tokens=3, completion_tokens=2, total_tokens=5, provider="openai")
  metrics = MetricsChunk(duration=0.12, time_to_first_chunk=0.01, chunk_count=2)
  response = AgentResponse(chunks=[TextChunk(data="hi"), usage, metrics])
  assert response.usage is usage
  assert response.metrics is metrics
  assert response.text() == "hi"


def test_usage_chunk_maps_openai_and_anthropic_fields():
  from claia.core.architectures.api.wire import usage_chunk

  openai = usage_chunk(
    {
      "input_tokens": 10,
      "output_tokens": 4,
      "total_tokens": 14,
      "input_tokens_details": {"cached_tokens": 2},
      "output_tokens_details": {"reasoning_tokens": 1},
    },
    provider="openai",
    provider_model="gpt-4o-mini",
    finish_reason="completed",
  )
  assert openai.prompt_tokens == 10
  assert openai.completion_tokens == 4
  assert openai.cached_tokens == 2
  assert openai.reasoning_tokens == 1
  assert openai.provider == "openai"

  anthropic = usage_chunk(
    {"input_tokens": 8, "output_tokens": 3, "cache_read_input_tokens": 5},
    provider="anthropic",
    provider_model="claude-sonnet-5",
  )
  assert anthropic.prompt_tokens == 8
  assert anthropic.total_tokens == 11
  assert anthropic.cached_tokens == 5
  assert usage_chunk(None, provider="x", provider_model="y") is None


def test_agent_response_iterates_then_aggregates():
  def gen():
    yield TextChunk(data="a")
    yield TextChunk(data="b")

  response = AgentResponse(gen())
  assert "".join(c.data for c in response) == "ab"
  assert response.text() == "ab"
  assert list(response) == []
