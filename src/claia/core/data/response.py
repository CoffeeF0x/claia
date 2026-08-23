"""
AgentResponse — one streamed response up the serving stack.

Iterate for chunks (text, tool, image, audio, usage, metrics). After
exhaustion the same object is the aggregate: collected chunks,
completion state, concatenated text, and the usage / metrics chunks
if any were yielded.
"""

from __future__ import annotations

from typing import Any, Iterator, List, Optional

from .chunks import BaseChunk, MetricsChunk, TextChunk, UsageChunk


class AgentResponse:
  """Streaming-first generate result.

  Wraps the deployment relay generator. Iterating yields chunks and
  collects them. A second pass after exhaustion yields nothing and
  leaves the aggregate fields intact.
  """

  def __init__(
    self,
    generator: Optional[Iterator[BaseChunk]] = None,
    *,
    chunks: Optional[List[BaseChunk]] = None,
    complete: bool = True,
    error: Optional[Any] = None,
  ):
    self._generator: Optional[Iterator[BaseChunk]] = generator
    self.chunks: List[BaseChunk] = list(chunks) if chunks is not None else []
    self.complete = complete
    self.error = error

  def bind(self, generator: Iterator[BaseChunk]) -> "AgentResponse":
    """Attach the relay generator. Used by the deployment that owns this response."""
    self._generator = generator
    return self

  def __iter__(self) -> Iterator[BaseChunk]:
    if self._generator is not None:
      generator, self._generator = self._generator, None
      for chunk in generator:
        self.chunks.append(chunk)
        yield chunk

  def is_success(self) -> bool:
    return self.complete and self.error is None

  def iter_text(self) -> Iterator[str]:
    """Yield string payloads from ``TextChunk`` items."""
    for chunk in self.chunks:
      if isinstance(chunk, TextChunk):
        yield chunk.data if isinstance(chunk.data, str) else str(chunk.data)

  def text(self) -> str:
    """Concatenate all text chunk payloads."""
    return "".join(self.iter_text())

  @property
  def usage(self) -> Optional[UsageChunk]:
    """The ``UsageChunk`` from this stream, if any."""
    for chunk in reversed(self.chunks):
      if isinstance(chunk, UsageChunk):
        return chunk
    return None

  @property
  def metrics(self) -> Optional[MetricsChunk]:
    """The ``MetricsChunk`` from this stream, if any."""
    for chunk in reversed(self.chunks):
      if isinstance(chunk, MetricsChunk):
        return chunk
    return None

  def to_dict(self) -> dict:
    return {
      "chunks": [c.to_dict() for c in self.chunks],
      "complete": self.complete,
      "error": self.error,
      "text": self.text(),
    }
