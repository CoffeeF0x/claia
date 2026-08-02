"""Image chunk — streamed image bytes."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ...enums.data import ImageFormat, MediaType

from .base import BaseChunk


class ImageChunk(BaseChunk):
  """Streamed image content (``bytes`` in ``data``)."""

  def __init__(
    self,
    data: bytes = b"",
    name: str = "image",
    format: ImageFormat = ImageFormat.PNG,
    metadata: Optional[Dict[str, Any]] = None,
  ):
    super().__init__(
      type=MediaType.IMAGE,
      format=format,
      name=name,
      metadata=metadata,
      data=data,
    )
