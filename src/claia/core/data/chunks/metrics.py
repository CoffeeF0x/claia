"""Metrics chunk — stream metering from the deployment relay."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ...enums.data import ApplicationFormat, MediaType

from .base import BaseChunk


class MetricsChunk(BaseChunk):
  """Timings and chunk counts for one generate stream.

  Populated by the deployment relay. Agents never append this to
  the streaming message.
  """

  def __init__(
    self,
    duration: Optional[float] = None,
    time_to_first_chunk: Optional[float] = None,
    chunk_count: Optional[int] = None,
    name: str = "metrics",
    metadata: Optional[Dict[str, Any]] = None,
  ):
    super().__init__(
      type=MediaType.APPLICATION,
      format=ApplicationFormat.JSON,
      name=name,
      metadata=metadata,
      data={
        "duration": duration,
        "time_to_first_chunk": time_to_first_chunk,
        "chunk_count": chunk_count,
      },
    )
    self.duration = duration
    self.time_to_first_chunk = time_to_first_chunk
    self.chunk_count = chunk_count
