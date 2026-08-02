"""
ModelDefinition dataclass.

A ``ModelDefinition`` is pure metadata about a model — its display title,
aliases, supported deployments and architectures, capabilities, and
input/output contracts. It does not implement model behaviour; that
lives in the corresponding architecture plugin.

Definition plugins return a dict of ``{model_name: ModelDefinition}``
which the framework merges across all installed providers.

``supported_inputs`` is the model IO contract used by
``BaseDeployment.translate``. Entries are ``ArtifactType`` values and/or
complex types (``MessageSequence``, ``MessageSequenceOrdered``).

``tag_overrides`` lets a definition swap the global default
``TagSpec`` for one or more ``TagType`` values when this model emits
non-default delimiter strings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Type

from ..enums.data import ArtifactType
from ..modality import Modality
from ..parser.types import TagSpec, TagType


_MODALITY_TO_ARTIFACT = {
  Modality.TEXT: ArtifactType.TEXT,
  Modality.IMAGE: ArtifactType.IMAGE,
  Modality.AUDIO: ArtifactType.AUDIO,
}


def artifacts_from_modalities(modalities: Optional[List[Modality]]) -> List[ArtifactType]:
  """Map coarse ``Modality`` lists to ``ArtifactType`` values."""
  if not modalities:
    return [ArtifactType.TEXT]
  out: List[ArtifactType] = []
  for modality in modalities:
    artifact_type = _MODALITY_TO_ARTIFACT.get(modality)
    if artifact_type is not None and artifact_type not in out:
      out.append(artifact_type)
  return out or [ArtifactType.TEXT]


def default_supported_inputs() -> List[Any]:
  """Default chat contract: text artifacts shaped as a message sequence."""
  from claia.core.data.models.conversation.message_sequence import MessageSequence
  return [ArtifactType.TEXT, MessageSequence]


@dataclass
class ModelDefinition:
  """Metadata describing a single model.

  ``supported_inputs`` lists what the model accepts after deployment
  translation: ``ArtifactType`` values and optional complex types
  (``MessageSequence`` / ``MessageSequenceOrdered``).
  """
  title: Optional[str] = None
  aliases: Optional[List[str]] = None
  company: Optional[str] = None
  deployments: Optional[List[str]] = None
  architectures: Optional[List[str]] = None
  description: Optional[str] = None
  parameters: Optional[str] = None
  context_length: Optional[int] = None
  capabilities: Optional[List[str]] = None
  license: Optional[str] = None
  url: Optional[str] = None
  identifiers: Optional[Dict[str, str]] = None
  input_modalities: List[Modality] = field(
    default_factory=lambda: [Modality.TEXT]
  )
  output_modalities: List[Modality] = field(
    default_factory=lambda: [Modality.TEXT]
  )
  supported_inputs: List[Any] = field(default_factory=default_supported_inputs)
  tag_overrides: Optional[Dict[TagType, TagSpec]] = None

  def artifact_types(self) -> List[ArtifactType]:
    """ArtifactType entries from ``supported_inputs``."""
    return [x for x in (self.supported_inputs or []) if isinstance(x, ArtifactType)]

  def sequence_class(self) -> Optional[Type]:
    """Preferred message-sequence class, if any.

    ``MessageSequenceOrdered`` wins when both sequence types are listed.
    """
    from claia.core.data.models.conversation.message_sequence import (
      MessageSequence,
      MessageSequenceOrdered,
    )
    inputs = self.supported_inputs or []
    if MessageSequenceOrdered in inputs:
      return MessageSequenceOrdered
    if MessageSequence in inputs:
      return MessageSequence
    return None

  def __post_init__(self) -> None:
    # Expand default TEXT-only artifact entries when modalities advertise more.
    arts = self.artifact_types()
    if arts == [ArtifactType.TEXT] and self.input_modalities:
      derived = artifacts_from_modalities(self.input_modalities)
      if derived != [ArtifactType.TEXT]:
        complex_types = [
          x for x in (self.supported_inputs or [])
          if not isinstance(x, ArtifactType)
        ]
        self.supported_inputs = [*derived, *complex_types]
