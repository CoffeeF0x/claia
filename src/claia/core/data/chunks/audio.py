"""Audio chunk — streamed audio bytes."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ...enums.data import AudioFormat, MediaType

from .base import BaseChunk


class AudioChunk(BaseChunk):
  """Streamed audio content (``bytes`` in ``data``)."""

  def __init__(
    self,
    data: bytes = b"",
    name: str = "audio",
    format: AudioFormat = AudioFormat.WAV,
    metadata: Optional[Dict[str, Any]] = None,
  ):
    super().__init__(
      type=MediaType.AUDIO,
      format=format,
      name=name,
      metadata=metadata,
      data=data,
    )
