"""
ModelDefinition dataclass.

A ``ModelDefinition`` is pure metadata about a model — its display title,
aliases, supported deployments and architectures, capabilities, and
input/output contracts. It does not implement model behaviour; that
lives in the corresponding architecture plugin.

Definition plugins return a dict of ``{model_name: ModelDefinition}``
which the framework merges across all installed providers.

``supported_artifacts`` / ``sequence_kind`` are the model IO contract
used by ``BaseDeployment.translate``. Coarse ``Modality`` lists remain
for application-level filtering.

``tag_overrides`` lets a definition swap the global default
``TagSpec`` for one or more ``TagType`` values when this model emits
non-default delimiter strings (e.g., a model that uses
``<tool_call>``/``</tool_call>`` instead of ``[TOOL_CALL]``).
Resolution happens via ``claia.core.parser.resolve_tag_specs``.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..enums.data import ArtifactType, SequenceKind
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


@dataclass
class ModelDefinition:
  """Metadata describing a single model.

  Most fields default to ``None`` so that providers can contribute
  partial definitions; the framework merges definitions across
  providers, preferring later non-None values.

  ``supported_artifacts`` lists native ``ArtifactType`` values the
  model can ingest after deployment translation. ``sequence_kind``
  selects how the active thread is shaped (flat / message / ordered).

  ``input_modalities`` / ``output_modalities`` remain for coarse
  application filtering; prefer ``supported_artifacts`` at the
  deployment → model boundary.

  ``tag_overrides`` is a per-``TagType`` replacement map for the
  global default ``TagSpec`` registry. ``None`` (the default) means
  the model uses the global defaults for every tag type. Entries in
  the map fully replace the corresponding default; there is no
  field-level merging within a ``TagSpec`` (see plan §3.7).
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
  supported_artifacts: List[ArtifactType] = field(
    default_factory=lambda: [ArtifactType.TEXT]
  )
  sequence_kind: SequenceKind = SequenceKind.MESSAGE
  tag_overrides: Optional[Dict[TagType, TagSpec]] = None

  def __post_init__(self) -> None:
    # Expand default TEXT-only artifacts when modalities advertise more.
    if self.supported_artifacts == [ArtifactType.TEXT] and self.input_modalities:
      derived = artifacts_from_modalities(self.input_modalities)
      if derived != [ArtifactType.TEXT]:
        self.supported_artifacts = derived
