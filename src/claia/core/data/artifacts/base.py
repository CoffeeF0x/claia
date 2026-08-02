"""
Base artifact — durable IO payload with identity and conversion lineage.
"""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union

from ..common import DataObject
from ...enums.data import MediaType
from ..common.data_object import FormatEnum


class BaseArtifact(DataObject, ABC):
  """Durable content object passed into models.

  Adds ``guid`` identity and optional ``original`` guid pointing at the
  pre-conversion artifact when this one was derived.
  """

  def __init__(
    self,
    type: MediaType,
    format: FormatEnum,
    name: str = "untitled",
    metadata: Optional[Dict[str, Any]] = None,
    guid: Optional[str] = None,
    original: Optional[str] = None,
    size: int = 0,
    created_at: Optional[float] = None,
    updated_at: Optional[float] = None,
  ):
    super().__init__(type=type, format=format, name=name, metadata=metadata)
    self.guid = guid or str(uuid.uuid4())
    self.original = original
    self.size = size
    self.created_at = created_at or time.time()
    self.updated_at = updated_at or self.created_at
    self._content: Optional[Any] = None
    self._content_loaded = False

  # Back-compat alias used by Conversation/CLI code that still says ``id``.
  @property
  def id(self) -> str:
    return self.guid

  @id.setter
  def id(self, value: str) -> None:
    self.guid = value

  @abstractmethod
  def load_content(self) -> Any:
    """Return in-memory content for this artifact."""

  def has_content_loaded(self) -> bool:
    return self._content_loaded

  def clear_content_cache(self) -> None:
    self._content = None
    self._content_loaded = False

  def to_dict(self) -> Dict[str, Any]:
    data = super().to_dict()
    data.update({
      "guid": self.guid,
      "id": self.guid,
      "original": self.original,
      "size": self.size,
      "created_at": self.created_at,
      "updated_at": self.updated_at,
      "media_type": self.media_type,
    })
    return data

  @classmethod
  @abstractmethod
  def from_dict(cls, data: Dict[str, Any]) -> BaseArtifact:
    """Deserialize an artifact from a plain dict."""

  def __repr__(self) -> str:
    return (
      f"<{self.__class__.__name__} guid={self.guid[:8]}... "
      f"name={self.name!r} media_type={self.media_type!r}>"
    )
