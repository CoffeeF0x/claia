"""
Base chunk — streamed content piece produced by a model.
"""

from __future__ import annotations

from abc import ABC
from typing import Any, Dict, Optional

from ..common import DataObject
from ..common.data_object import FormatEnum
from ...enums.data import MediaType


class BaseChunk(DataObject, ABC):
  """Single content piece in a model response stream.

  Chunks are never converted in-flight, so they do not carry ``guid`` or
  ``original``. Class identity is the discriminator (no ``kind`` field).
  """

  def __init__(
    self,
    type: MediaType,
    format: FormatEnum,
    name: str = "chunk",
    metadata: Optional[Dict[str, Any]] = None,
    data: Any = None,
  ):
    super().__init__(type=type, format=format, name=name, metadata=metadata)
    self.data = data

  def to_dict(self) -> Dict[str, Any]:
    payload = super().to_dict()
    payload["data"] = self.data
    payload["media_type"] = self.media_type
    return payload
