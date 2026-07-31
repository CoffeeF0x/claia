"""
Shared base for artifacts and chunks.

``DataObject`` carries media identity (IANA type + format subtype), a
human label, and a freeform metadata bag. Artifacts and chunks specialize
from here.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional, Union

from claia.core.enums.data import (
  ApplicationFormat,
  AudioFormat,
  ImageFormat,
  MediaType,
  TextFormat,
  VideoFormat,
)

FormatEnum = Union[
  TextFormat,
  ImageFormat,
  AudioFormat,
  VideoFormat,
  ApplicationFormat,
  Enum,
]


class DataObject:
  """Common fields shared by artifacts and chunks."""

  def __init__(
    self,
    type: MediaType,
    format: FormatEnum,
    name: str = "untitled",
    metadata: Optional[Dict[str, Any]] = None,
  ):
    self.type = type
    self.format = format
    self.name = name
    self.metadata = metadata or {}

  @property
  def media_type(self) -> str:
    """Render ``type/format`` as a MIME string."""
    return f"{self.type.value}/{self.format.value}"

  def to_dict(self) -> Dict[str, Any]:
    return {
      "type": self.type.value,
      "format": self.format.value,
      "name": self.name,
      "metadata": self.metadata,
    }

  def __repr__(self) -> str:
    return (
      f"<{self.__class__.__name__} name={self.name!r} "
      f"media_type={self.media_type!r}>"
    )
