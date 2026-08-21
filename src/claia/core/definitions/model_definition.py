"""
ModelDefinition dataclass.

A ``ModelDefinition`` is pure metadata about a model — its display title,
aliases, supported deployments and architectures, capabilities, and
input/output contracts. It does not implement model behaviour; that
lives in the corresponding architecture (the model class).

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

from dataclasses import MISSING, dataclass, field, fields
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
  from ..data.models.conversation.message_sequence import MessageSequence
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
    from ..data.models.conversation.message_sequence import (
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


########################################################################
#                         DEFINITION MERGER                            #
########################################################################
_ORDERED_UNION_FIELDS = frozenset({
  "aliases",
  "deployments",
  "architectures",
  "capabilities",
  "supported_inputs",
})
_OVERLAY_DICT_FIELDS = frozenset({
  "identifiers",
  "tag_overrides",
})
_DEFAULT_SENTINEL_FIELDS = frozenset({
  "input_modalities",
  "output_modalities",
})


def _field_default(f) -> Any:
  """Return the declared default for a ``ModelDefinition`` field."""
  if f.default_factory is not MISSING:
    return f.default_factory()
  if f.default is not MISSING:
    return f.default
  return None


def _ordered_union(existing: Any, incoming: Any) -> Any:
  """Concatenate two sequences, drop duplicates, keep first-seen order."""
  result: List[Any] = []
  for item in (*(existing or []), *(incoming or [])):
    if item not in result:
      result.append(item)
  if not result:
    return existing if existing is not None else incoming
  return result


def _overlay_dict(existing: Any, incoming: Any) -> Any:
  """Shallow-merge two mappings; incoming wins per key."""
  if not existing and not incoming:
    return existing if existing is not None else incoming
  merged: Dict[Any, Any] = {}
  if existing:
    merged.update(existing)
  if incoming:
    merged.update(incoming)
  return merged


def merge_model_definitions(
  existing: ModelDefinition,
  incoming: ModelDefinition,
) -> ModelDefinition:
  """Merge two ``ModelDefinition`` objects for the same model name.

  Walks ``dataclasses.fields(ModelDefinition)`` so new fields pick up
  a sane default instead of being dropped. Per-field rules:

  - Ordered-union lists (``aliases``, ``deployments``, ``architectures``,
    ``capabilities``, ``supported_inputs``): concatenate, dedupe, keep
    first-seen order.
  - Overlay dicts (``identifiers``, ``tag_overrides``): incoming wins
    per key. Tag overrides replace per ``TagType``; no deep-merge of
    individual ``TagSpec`` fields.
  - Default-sentinel fields (``input_modalities``, ``output_modalities``):
    incoming wins only when it differs from the field's declared
    default, so a later provider that leaves the ``[Modality.TEXT]``
    default does not clobber an earlier richer list.
  - Everything else: incoming if not ``None``, else existing.
  """
  values: Dict[str, Any] = {}
  for f in fields(ModelDefinition):
    ev = getattr(existing, f.name)
    iv = getattr(incoming, f.name)
    if f.name in _ORDERED_UNION_FIELDS:
      values[f.name] = _ordered_union(ev, iv)
    elif f.name in _OVERLAY_DICT_FIELDS:
      values[f.name] = _overlay_dict(ev, iv)
    elif f.name in _DEFAULT_SENTINEL_FIELDS:
      values[f.name] = iv if iv != _field_default(f) else ev
    else:
      values[f.name] = iv if iv is not None else ev
  return ModelDefinition(**values)
