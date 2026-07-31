"""Raw artifact — unknown / misc ``application/octet-stream``."""

from __future__ import annotations

import base64
import logging
import time
from typing import Any, Dict

from claia.core.enums.data import ApplicationFormat, MediaType

from .base import BaseArtifact


logger = logging.getLogger(__name__)


class RawArtifact(BaseArtifact):
  """Opaque bytes when no better artifact type applies."""

  def __init__(self, name: str = "untitled.bin", **kwargs):
    kwargs.pop("type", None)
    kwargs.pop("format", None)
    super().__init__(
      type=MediaType.APPLICATION,
      format=ApplicationFormat.OCTET_STREAM,
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
  def from_dict(cls, data: Dict[str, Any]) -> RawArtifact:
    artifact = cls(
      name=data.get("name", "untitled.bin"),
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
        logger.warning(f"Failed to decode raw content: {exc}")
    return artifact

  @classmethod
  def from_bytes(cls, data: bytes, name: str, **kwargs) -> RawArtifact:
    artifact = cls(name=name, **kwargs)
    artifact.set_content(data)
    return artifact
