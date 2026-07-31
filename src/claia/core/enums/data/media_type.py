"""IANA top-level media types."""

from enum import Enum


class MediaType(Enum):
  """IANA top-level media type (the left half of ``type/subtype``)."""

  APPLICATION = "application"
  AUDIO = "audio"
  EXAMPLE = "example"
  FONT = "font"
  HAPTICS = "haptics"
  IMAGE = "image"
  MESSAGE = "message"
  MODEL = "model"
  MULTIPART = "multipart"
  TEXT = "text"
  VIDEO = "video"
