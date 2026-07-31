"""
Helpers for draining ``BaseModel.generate`` into chunks + ModelResponse.
"""

from __future__ import annotations

from typing import Any, Generator, Iterator, Sequence, Union

from claia.core.data.artifacts import BaseArtifact
from claia.core.data.chunks import BaseChunk, TextChunk
from claia.core.data.response import ModelResponse


def normalize_chunk(item: Any) -> BaseChunk:
  """Coerce a yielded item into a ``BaseChunk``."""
  if isinstance(item, BaseChunk):
    return item
  if isinstance(item, str):
    return TextChunk(data=item)
  if isinstance(item, bytes):
    from claia.core.data.chunks import RawChunk
    return RawChunk(data=item)
  return TextChunk(data=str(item))


def drain_generate(
  model: Any,
  artifacts: Sequence[BaseArtifact],
  runtime_kwargs: dict,
) -> Generator[BaseChunk, None, ModelResponse]:
  """Call ``model.generate``, yield chunks, return a ``ModelResponse``.

  Supports both direct ``ModelResponse`` returns and streaming generators
  that yield chunks (or legacy strings) and return a ``ModelResponse``
  or plain string.
  """
  result = model.generate(artifacts, **runtime_kwargs)

  if isinstance(result, ModelResponse):
    for chunk in result.chunks:
      yield chunk
    return result

  if not hasattr(result, "__iter__") or isinstance(result, (str, bytes)):
    # Unexpected scalar — wrap as a single text chunk.
    chunk = normalize_chunk(result)
    response = ModelResponse(chunks=[chunk], complete=True)
    yield chunk
    return response

  chunks = []
  try:
    iterator: Iterator = iter(result)
    while True:
      item = next(iterator)
      chunk = normalize_chunk(item)
      chunks.append(chunk)
      yield chunk
  except StopIteration as stop:
    value = stop.value
    if isinstance(value, ModelResponse):
      if not value.chunks:
        value.chunks = list(chunks)
      return value
    return ModelResponse(
      chunks=list(chunks),
      complete=True,
      metadata={"return": value} if value is not None else {},
    )
