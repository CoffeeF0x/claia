"""IANA ``video/*`` subtype tokens used by CLAIA."""

from enum import Enum


class VideoFormat(Enum):
  """Curated ``video`` subtypes. Enum ready; VideoArtifact comes later."""

  MP4 = "mp4"
  WEBM = "webm"
  OGG = "ogg"
  MPEG = "mpeg"
  QUICKTIME = "quicktime"
