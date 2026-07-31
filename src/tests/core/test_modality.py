"""
Tests for modality declarations and the new chunk / response contract.

Covers ``Modality``, content chunk classes, and ``ModelResponse``.
"""

from claia.core.data.chunks import AudioChunk, ImageChunk, TextChunk
from claia.core.data.response import ModelResponse
from claia.core.enums.data import AudioFormat, ImageFormat, MediaType, TextFormat
from claia.core.modality import Modality


def test_modality_values():
  values = {m.value for m in Modality}
  assert {"text", "image", "audio", "video", "embedding"} <= values


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


def test_model_response_iter_text():
  response = ModelResponse(
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


def test_model_response_error():
  response = ModelResponse(chunks=[], complete=False, error="boom")
  assert not response.is_success()
