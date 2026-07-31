"""IANA ``image/*`` subtype tokens used by CLAIA."""

from enum import Enum


class ImageFormat(Enum):
  """Curated ``image`` subtypes. Grow as needed."""

  PNG = "png"
  JPEG = "jpeg"
  WEBP = "webp"
  GIF = "gif"
  BMP = "bmp"
  TIFF = "tiff"
  SVG_XML = "svg+xml"
  X_ICON = "x-icon"
