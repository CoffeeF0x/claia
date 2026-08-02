"""File artifact — known document-ish ``application/*`` payloads."""

from __future__ import annotations

import base64
import logging
import time
from typing import Any, Dict, Optional

from ...enums.data import ApplicationFormat, MediaType

from .base import BaseArtifact


logger = logging.getLogger(__name__)

_EXT_TO_FORMAT = {
  "pdf": ApplicationFormat.PDF,
  "json": ApplicationFormat.JSON,
  "xml": ApplicationFormat.XML,
  "zip": ApplicationFormat.ZIP,
  "docx": ApplicationFormat.DOCX,
  "xlsx": ApplicationFormat.XLSX,
}


class FileArtifact(BaseArtifact):
  """Known file types we may convert later (pdf, docx, …)."""

  def __init__(
    self,
    name: str = "untitled.bin",
    format: ApplicationFormat = ApplicationFormat.OCTET_STREAM,
    **kwargs,
  ):
    kwargs.pop("type", None)
    if not isinstance(format, ApplicationFormat):
      format = ApplicationFormat.OCTET_STREAM
    super().__init__(
      type=MediaType.APPLICATION,
      format=format,
      name=name,
      **kwargs,
    )

  def load_content(self) -> bytes:
    if self._content_loaded and self._content is not None:
      return self._content
    return b""

  def set_content(self, data: bytes) -> None:
    self._content = data
    self._content_loaded = True
    self.size = len(data)
    self.updated_at = time.time()

  @property
  def content(self) -> bytes:
    return self.load_content()

  def to_dict(self) -> Dict[str, Any]:
    data = super().to_dict()
    if self._content_loaded and self._content is not None:
      data["content_encoding"] = "base64"
      data["content"] = base64.b64encode(self._content).decode("ascii")
    return data

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> FileArtifact:
    fmt_value = data.get("format", ApplicationFormat.OCTET_STREAM.value)
    try:
      fmt = ApplicationFormat(fmt_value)
    except ValueError:
      fmt = ApplicationFormat.OCTET_STREAM
    artifact = cls(
      name=data.get("name", "untitled.bin"),
      format=fmt,
      guid=data.get("guid") or data.get("id"),
      original=data.get("original"),
      size=data.get("size", 0),
      metadata=data.get("metadata", {}),
      created_at=data.get("created_at"),
      updated_at=data.get("updated_at"),
    )
    if data.get("content_encoding") == "base64" and data.get("content"):
      try:
        artifact._content = base64.b64decode(data["content"])
        artifact._content_loaded = True
      except Exception as exc:
        logger.warning(f"Failed to decode file content: {exc}")
    return artifact

  @classmethod
  def from_bytes(
    cls,
    data: bytes,
    name: str,
    format: Optional[ApplicationFormat] = None,
    **kwargs,
  ) -> FileArtifact:
    if format is None:
      ext = name.lower().rsplit(".", 1)[-1] if "." in name else ""
      format = _EXT_TO_FORMAT.get(ext, ApplicationFormat.OCTET_STREAM)
    artifact = cls(name=name, format=format, **kwargs)
    artifact.set_content(data)
    return artifact

  @classmethod
  def from_path(cls, source: str, **kwargs) -> FileArtifact:
    import os
    name = kwargs.pop("name", os.path.basename(source))
    ext = name.lower().rsplit(".", 1)[-1] if "." in name else ""
    format = kwargs.pop("format", _EXT_TO_FORMAT.get(ext, ApplicationFormat.OCTET_STREAM))
    artifact = cls(name=name, format=format, **kwargs)
    artifact.metadata["source_uri"] = source
    return artifact
