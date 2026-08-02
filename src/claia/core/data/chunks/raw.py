"""Raw chunk — opaque streamed bytes."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ...enums.data import ApplicationFormat, MediaType

from .base import BaseChunk


class RawChunk(BaseChunk):
  """Opaque bytes the consumer must not assume are typed."""

  def __init__(
    self,
    data: bytes = b"",
    name: str = "raw",
    metadata: Optional[Dict[str, Any]] = None,
  ):
    super().__init__(
      type=MediaType.APPLICATION,
      format=ApplicationFormat.OCTET_STREAM,
      name=name,
      metadata=metadata,
      data=data,
    )
