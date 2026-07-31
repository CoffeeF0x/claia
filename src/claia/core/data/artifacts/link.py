"""Link artifact — content *is* a URI (``text/uri-list``)."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from claia.core.enums.data import MediaType, TextFormat

from .base import BaseArtifact


class LinkArtifact(BaseArtifact):
  """URI reference artifact. Payload is the URI string."""

  def __init__(
    self,
    name: str = "link",
    uri: str = "",
    title: Optional[str] = None,
    **kwargs,
  ):
    kwargs.pop("type", None)
    kwargs.pop("format", None)
    super().__init__(
      type=MediaType.TEXT,
      format=TextFormat.URI_LIST,
      name=name,
      **kwargs,
    )
    self.uri = uri
    if title is not None:
      self.metadata["title"] = title
    if uri:
      self._content = uri
      self._content_loaded = True
      self.size = len(uri.encode("utf-8"))

  def load_content(self) -> str:
    if self._content_loaded and self._content is not None:
      return self._content
    return self.uri or ""

  def set_content(self, uri: str) -> None:
    self.uri = uri
    self._content = uri
    self._content_loaded = True
    self.size = len(uri.encode("utf-8"))
    self.updated_at = time.time()

  @property
  def content(self) -> str:
    return self.load_content()

  def to_dict(self) -> Dict[str, Any]:
    data = super().to_dict()
    data["uri"] = self.uri
    if self.metadata.get("title") is not None:
      data["title"] = self.metadata["title"]
    return data

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> LinkArtifact:
    return cls(
      name=data.get("name", "link"),
      uri=data.get("uri") or data.get("content") or "",
      title=data.get("title") or data.get("metadata", {}).get("title"),
      guid=data.get("guid") or data.get("id"),
      original=data.get("original"),
      size=data.get("size", 0),
      metadata=data.get("metadata", {}),
      created_at=data.get("created_at"),
      updated_at=data.get("updated_at"),
    )

  @classmethod
  def from_uri(
    cls,
    uri: str,
    name: Optional[str] = None,
    title: Optional[str] = None,
    **kwargs,
  ) -> LinkArtifact:
    return cls(
      name=name or uri,
      uri=uri,
      title=title,
      **kwargs,
    )
