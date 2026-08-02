"""Audio artifact — bytes payload under ``MediaType.AUDIO``."""

from __future__ import annotations

import base64
import logging
import time
from typing import Any, Dict, Optional

from ...enums.data import AudioFormat, MediaType

from .base import BaseArtifact


logger = logging.getLogger(__name__)

_EXT_TO_FORMAT = {
  "mp3": AudioFormat.MPEG,
  "wav": AudioFormat.WAV,
  "ogg": AudioFormat.OGG,
  "flac": AudioFormat.FLAC,
  "aac": AudioFormat.AAC,
  "m4a": AudioFormat.MP4,
  "wma": AudioFormat.X_MS_WMA,
  "opus": AudioFormat.OPUS,
}


class AudioArtifact(BaseArtifact):
  """Audio content stored as bytes."""

  def __init__(
    self,
    name: str = "untitled.mp3",
    format: AudioFormat = AudioFormat.MPEG,
    duration: Optional[float] = None,
    sample_rate: Optional[int] = None,
    channels: Optional[int] = None,
    **kwargs,
  ):
    kwargs.pop("type", None)
    if not isinstance(format, AudioFormat):
      format = AudioFormat.MPEG
    super().__init__(type=MediaType.AUDIO, format=format, name=name, **kwargs)
    self.duration = duration
    self.sample_rate = sample_rate
    self.channels = channels
    if duration is not None:
      self.metadata["duration"] = duration
    if sample_rate is not None:
      self.metadata["sample_rate"] = sample_rate
    if channels is not None:
      self.metadata["channels"] = channels

  def load_content(self) -> bytes:
    if self._content_loaded and self._content is not None:
      return self._content
    return b""

  def set_content(self, audio_data: bytes) -> None:
    self._content = audio_data
    self._content_loaded = True
    self.size = len(audio_data)
    self.updated_at = time.time()

  @property
  def content(self) -> bytes:
    return self.load_content()

  def to_dict(self) -> Dict[str, Any]:
    data = super().to_dict()
    if self.duration is not None:
      data["duration"] = self.duration
    if self.sample_rate is not None:
      data["sample_rate"] = self.sample_rate
    if self.channels is not None:
      data["channels"] = self.channels
    if self._content_loaded and self._content is not None:
      data["content_encoding"] = "base64"
      data["content"] = base64.b64encode(self._content).decode("ascii")
    return data

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> AudioArtifact:
    fmt_value = data.get("format", AudioFormat.MPEG.value)
    try:
      fmt = AudioFormat(fmt_value)
    except ValueError:
      fmt = _EXT_TO_FORMAT.get(str(fmt_value).lower(), AudioFormat.MPEG)
    artifact = cls(
      name=data.get("name", "untitled.mp3"),
      format=fmt,
      guid=data.get("guid") or data.get("id"),
      original=data.get("original"),
      size=data.get("size", 0),
      duration=data.get("duration") or data.get("metadata", {}).get("duration"),
      sample_rate=data.get("sample_rate") or data.get("metadata", {}).get("sample_rate"),
      channels=data.get("channels") or data.get("metadata", {}).get("channels"),
      metadata=data.get("metadata", {}),
      created_at=data.get("created_at"),
      updated_at=data.get("updated_at"),
    )
    if data.get("content_encoding") == "base64" and data.get("content"):
      try:
        artifact._content = base64.b64decode(data["content"])
        artifact._content_loaded = True
      except Exception as exc:
        logger.warning(f"Failed to decode audio content: {exc}")
    return artifact

  @classmethod
  def from_bytes(cls, audio_data: bytes, name: str, **kwargs) -> AudioArtifact:
    if "format" not in kwargs:
      ext = name.lower().rsplit(".", 1)[-1] if "." in name else "mp3"
      kwargs["format"] = _EXT_TO_FORMAT.get(ext, AudioFormat.MPEG)
    artifact = cls(name=name, **kwargs)
    artifact.set_content(audio_data)
    return artifact

  @classmethod
  def from_path(cls, source: str, **kwargs) -> AudioArtifact:
    import os
    name = kwargs.pop("name", os.path.basename(source))
    ext = name.lower().rsplit(".", 1)[-1] if "." in name else "mp3"
    format = kwargs.pop("format", _EXT_TO_FORMAT.get(ext, AudioFormat.MPEG))
    artifact = cls(name=name, format=format, **kwargs)
    artifact.metadata["source_uri"] = source
    return artifact
