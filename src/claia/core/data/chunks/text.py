"""Text chunk — token / delta / text piece."""

from __future__ import annotations

from typing import Any, Dict, Optional

from claia.core.enums.data import MediaType, TextFormat

from .base import BaseChunk


class TextChunk(BaseChunk):
  """Streamed text content (``str`` in ``data``)."""

  def __init__(
    self,
    data: str = "",
    name: str = "text",
    format: TextFormat = TextFormat.PLAIN,
    metadata: Optional[Dict[str, Any]] = None,
  ):
    super().__init__(
      type=MediaType.TEXT,
      format=format,
      name=name,
      metadata=metadata,
      data=data,
    )

  def __str__(self) -> str:
    return self.data if isinstance(self.data, str) else str(self.data or "")
