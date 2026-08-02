"""Artifact type discriminator — maps names to artifact classes."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Dict, Type

if TYPE_CHECKING:
  from ...data.artifacts import BaseArtifact


class ArtifactType(Enum):
  """Contract-level artifact kinds (separate from IANA ``MediaType``)."""

  TEXT = "text"
  IMAGE = "image"
  AUDIO = "audio"
  FILE = "file"
  LINK = "link"
  RAW = "raw"
  TOOL = "tool"

  def artifact_class(self) -> Type["BaseArtifact"]:
    """Return the concrete artifact class for this type."""
    return _ARTIFACT_CLASSES()[self]

  @classmethod
  def from_artifact(cls, artifact: "BaseArtifact") -> "ArtifactType":
    """Resolve ``ArtifactType`` from an artifact instance."""
    for artifact_type, artifact_cls in _ARTIFACT_CLASSES().items():
      if isinstance(artifact, artifact_cls):
        return artifact_type
    return cls.RAW


def _ARTIFACT_CLASSES() -> Dict[ArtifactType, Type["BaseArtifact"]]:
  from ...data.artifacts import (
    AudioArtifact,
    FileArtifact,
    ImageArtifact,
    LinkArtifact,
    RawArtifact,
    TextArtifact,
    ToolArtifact,
  )
  return {
    ArtifactType.TEXT: TextArtifact,
    ArtifactType.IMAGE: ImageArtifact,
    ArtifactType.AUDIO: AudioArtifact,
    ArtifactType.FILE: FileArtifact,
    ArtifactType.LINK: LinkArtifact,
    ArtifactType.RAW: RawArtifact,
    ArtifactType.TOOL: ToolArtifact,
  }
