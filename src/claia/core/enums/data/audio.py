"""IANA ``audio/*`` subtype tokens used by CLAIA."""

from enum import Enum


class AudioFormat(Enum):
  """Curated ``audio`` subtypes. Grow as needed."""

  WAV = "wav"
  MPEG = "mpeg"
  OGG = "ogg"
  FLAC = "flac"
  AAC = "aac"
  MP4 = "mp4"
  OPUS = "opus"
  X_MS_WMA = "x-ms-wma"
