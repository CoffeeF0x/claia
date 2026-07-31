"""Image artifact — bytes (optionally decoded via PIL)."""

from __future__ import annotations

import base64
import io
import logging
import time
from typing import Any, Dict, Optional, Tuple

from claia.core.enums.data import ImageFormat, MediaType

from .base import BaseArtifact


logger = logging.getLogger(__name__)

_EXT_TO_FORMAT = {
  "jpg": ImageFormat.JPEG,
  "jpeg": ImageFormat.JPEG,
  "png": ImageFormat.PNG,
  "gif": ImageFormat.GIF,
  "bmp": ImageFormat.BMP,
  "webp": ImageFormat.WEBP,
  "svg": ImageFormat.SVG_XML,
  "tiff": ImageFormat.TIFF,
  "tif": ImageFormat.TIFF,
  "ico": ImageFormat.X_ICON,
}


class ImageArtifact(BaseArtifact):
  """Image content stored as bytes, with optional PIL decode."""

  def __init__(
    self,
    name: str = "untitled.jpg",
    format: ImageFormat = ImageFormat.JPEG,
    width: Optional[int] = None,
    height: Optional[int] = None,
    content_bytes: Optional[bytes] = None,
    **kwargs,
  ):
    kwargs.pop("type", None)
    if not isinstance(format, ImageFormat):
      format = ImageFormat.JPEG
    super().__init__(type=MediaType.IMAGE, format=format, name=name, **kwargs)
    self.width = width
    self.height = height
    self._content_bytes = content_bytes
    if width is not None:
      self.metadata["width"] = width
    if height is not None:
      self.metadata["height"] = height
    if content_bytes is not None:
      self.size = len(content_bytes)

  def load_content(self):
    if self._content_loaded and self._content is not None:
      return self._content
    if self._content_bytes:
      try:
        from PIL import Image
        self._content = Image.open(io.BytesIO(self._content_bytes))
        self._content_loaded = True
        return self._content
      except ImportError:
        logger.warning("PIL not available, cannot load image object")
        return None
      except Exception as exc:
        logger.warning(f"Could not load image for {self.guid}: {exc}")
        return None
    return None

  def load_bytes(self) -> Optional[bytes]:
    if self._content_bytes:
      return self._content_bytes
    if self._content_loaded and self._content is not None:
      buffer = io.BytesIO()
      pil_format = self.format.name if self.format is not ImageFormat.JPEG else "JPEG"
      if self.format is ImageFormat.PNG:
        pil_format = "PNG"
      elif self.format is ImageFormat.WEBP:
        pil_format = "WEBP"
      elif self.format is ImageFormat.GIF:
        pil_format = "GIF"
      self._content.save(buffer, format=pil_format)
      self._content_bytes = buffer.getvalue()
      self.size = len(self._content_bytes)
      return self._content_bytes
    return None

  def set_content(self, image_obj) -> None:
    self._content = image_obj
    self._content_loaded = True
    self._content_bytes = None
    if hasattr(image_obj, "size"):
      self.width, self.height = image_obj.size
      self.metadata["width"] = self.width
      self.metadata["height"] = self.height
    self.updated_at = time.time()

  @property
  def content(self):
    return self.load_content()

  @property
  def dimensions(self) -> Optional[Tuple[int, int]]:
    if self.width and self.height:
      return (self.width, self.height)
    return None

  def to_dict(self) -> Dict[str, Any]:
    data = super().to_dict()
    if self.width is not None:
      data["width"] = self.width
    if self.height is not None:
      data["height"] = self.height
    content_bytes = self.load_bytes()
    if content_bytes:
      data["content_encoding"] = "base64"
      data["content"] = base64.b64encode(content_bytes).decode("ascii")
    return data

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> ImageArtifact:
    content_bytes = None
    if data.get("content_encoding") == "base64" and data.get("content"):
      try:
        content_bytes = base64.b64decode(data["content"])
      except Exception as exc:
        logger.warning(f"Failed to decode image content: {exc}")
    fmt_value = data.get("format", ImageFormat.JPEG.value)
    try:
      fmt = ImageFormat(fmt_value)
    except ValueError:
      # legacy uppercase format names
      try:
        fmt = ImageFormat[fmt_value.upper().replace("JPG", "JPEG")]
      except KeyError:
        fmt = ImageFormat.JPEG
    return cls(
      name=data.get("name", "untitled.jpg"),
      format=fmt,
      guid=data.get("guid") or data.get("id"),
      original=data.get("original"),
      size=data.get("size", 0),
      width=data.get("width") or data.get("metadata", {}).get("width"),
      height=data.get("height") or data.get("metadata", {}).get("height"),
      content_bytes=content_bytes,
      metadata=data.get("metadata", {}),
      created_at=data.get("created_at"),
      updated_at=data.get("updated_at"),
    )

  @classmethod
  def from_bytes(
    cls,
    image_data: bytes,
    name: str,
    format: Optional[ImageFormat] = None,
    **kwargs,
  ) -> ImageArtifact:
    if format is None:
      ext = name.lower().rsplit(".", 1)[-1] if "." in name else "jpg"
      format = _EXT_TO_FORMAT.get(ext, ImageFormat.JPEG)
    width = height = None
    image_obj = None
    try:
      from PIL import Image
      image_obj = Image.open(io.BytesIO(image_data))
      width, height = image_obj.size
    except Exception:
      pass
    artifact = cls(
      name=name,
      format=format,
      width=width,
      height=height,
      content_bytes=image_data,
      size=len(image_data),
      **kwargs,
    )
    if image_obj is not None:
      artifact._content = image_obj
      artifact._content_loaded = True
    artifact.updated_at = time.time()
    return artifact

  @classmethod
  def from_image(cls, image_obj, name: str, **kwargs) -> ImageArtifact:
    width, height = image_obj.size if hasattr(image_obj, "size") else (None, None)
    fmt = kwargs.pop("format", ImageFormat.PNG)
    artifact = cls(name=name, width=width, height=height, format=fmt, **kwargs)
    artifact.set_content(image_obj)
    return artifact

  @classmethod
  def from_path(cls, source: str, **kwargs) -> ImageArtifact:
    import os
    name = kwargs.pop("name", os.path.basename(source))
    ext = name.lower().rsplit(".", 1)[-1] if "." in name else "jpg"
    format = kwargs.pop("format", _EXT_TO_FORMAT.get(ext, ImageFormat.JPEG))
    artifact = cls(name=name, format=format, **kwargs)
    artifact.metadata["source_uri"] = source
    return artifact
