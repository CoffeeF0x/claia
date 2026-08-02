"""Text artifact — string payload under ``MediaType.TEXT``."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from ...enums.data import MediaType, TextFormat

from .base import BaseArtifact


_EXT_TO_FORMAT = {
  "txt": TextFormat.PLAIN,
  "md": TextFormat.MARKDOWN,
  "html": TextFormat.HTML,
  "htm": TextFormat.HTML,
  "css": TextFormat.CSS,
  "js": TextFormat.JAVASCRIPT,
  "xml": TextFormat.XML,
  "csv": TextFormat.CSV,
}


class TextArtifact(BaseArtifact):
  """Text content stored as a ``str``."""

  def __init__(
    self,
    name: str = "untitled.txt",
    format: TextFormat = TextFormat.PLAIN,
    encoding: str = "utf-8",
    **kwargs,
  ):
    if "type" in kwargs:
      kwargs.pop("type")
    super().__init__(
      type=MediaType.TEXT,
      format=format if isinstance(format, TextFormat) else TextFormat.PLAIN,
      name=name,
      **kwargs,
    )
    self.encoding = encoding
    self.metadata.setdefault("encoding", encoding)

  def load_content(self) -> str:
    if self._content_loaded and self._content is not None:
      return self._content
    return ""

  def set_content(self, content: str) -> None:
    self._content = content
    self._content_loaded = True
    self.size = len(content.encode(self.encoding))
    self.updated_at = time.time()

  @property
  def content(self) -> str:
    return self.load_content()

  def to_dict(self) -> Dict[str, Any]:
    data = super().to_dict()
    data["encoding"] = self.encoding
    if self._content_loaded and self._content is not None:
      data["content"] = self._content
    return data

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> TextArtifact:
    fmt_value = data.get("format", TextFormat.PLAIN.value)
    try:
      fmt = TextFormat(fmt_value)
    except ValueError:
      fmt = TextFormat.PLAIN
    artifact = cls(
      name=data.get("name", "untitled.txt"),
      format=fmt,
      encoding=data.get("encoding", "utf-8"),
      guid=data.get("guid") or data.get("id"),
      original=data.get("original"),
      size=data.get("size", 0),
      metadata=data.get("metadata", {}),
      created_at=data.get("created_at"),
      updated_at=data.get("updated_at"),
    )
    if data.get("content") is not None:
      artifact._content = data["content"]
      artifact._content_loaded = True
    return artifact

  @classmethod
  def from_content(
    cls,
    content: str,
    name: str,
    format: Optional[TextFormat] = None,
    encoding: str = "utf-8",
    **kwargs,
  ) -> TextArtifact:
    if format is None:
      ext = name.lower().rsplit(".", 1)[-1] if "." in name else "txt"
      format = _EXT_TO_FORMAT.get(ext, TextFormat.PLAIN)
    artifact = cls(name=name, format=format, encoding=encoding, **kwargs)
    artifact.set_content(content)
    return artifact

  @classmethod
  def from_path(cls, source: str, **kwargs) -> TextArtifact:
    import os
    name = kwargs.pop("name", os.path.basename(source))
    ext = name.lower().rsplit(".", 1)[-1] if "." in name else "txt"
    format = kwargs.pop("format", _EXT_TO_FORMAT.get(ext, TextFormat.PLAIN))
    artifact = cls(name=name, format=format, **kwargs)
    artifact.metadata["source_uri"] = source
    return artifact
