"""
Model response wrapper and stream delivery.

Generation returns a ``ModelResponse`` carrying content chunks plus
status fields (complete / error) and aggregate metadata (usage,
timings). Control signals are not chunks. ``GenerateStream`` wraps a
generate generator so callers never hand-roll terminal-value capture:
iterate for chunks, read ``.response`` after exhaustion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Generator, Iterator, List, Optional

from .chunks import BaseChunk, TextChunk


@dataclass
class ModelResponse:
  """Return value of model generation.

  Attributes:
    chunks: Content produced by the model.
    complete: Whether generation finished successfully / fully.
    error: Optional error info (message, code, or structured data).
    metadata: Provider extras (usage, finish_reason, …).
  """

  chunks: List[BaseChunk] = field(default_factory=list)
  complete: bool = True
  error: Optional[Any] = None
  metadata: Dict[str, Any] = field(default_factory=dict)

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

  def to_dict(self) -> Dict[str, Any]:
    return {
      "chunks": [c.to_dict() for c in self.chunks],
      "complete": self.complete,
      "error": self.error,
      "metadata": self.metadata,
    }


class GenerateStream:
  """Iterable over a generate stream that captures the terminal wrapper.

  Wraps a ``Generator[BaseChunk, None, ModelResponse]``. Iterating
  yields the chunks; once the stream is exhausted the generator's
  returned ``ModelResponse`` is available as ``.response``. Iterating
  again after exhaustion yields nothing and leaves ``response`` intact.
  """

  def __init__(self, generator: Generator[BaseChunk, None, "ModelResponse"]):
    self._generator: Optional[Generator] = generator
    self.response: Optional[ModelResponse] = None

  def __iter__(self) -> Iterator[BaseChunk]:
    if self._generator is not None:
      generator, self._generator = self._generator, None
      self.response = yield from generator
