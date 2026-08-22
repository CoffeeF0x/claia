"""
ModelDefinition dataclass.

A ``ModelDefinition`` is pure metadata about a model — its display title,
aliases, supported deployments and architectures, capabilities, and
input/output contracts. It does not implement model behaviour; that
lives in the corresponding architecture (the model class).

Definition plugins return a dict of ``{model_name: ModelDefinition}``
which the framework merges across all installed providers.

``inputs`` is the model IO contract used by
``Conversation.to_model_inputs``.
Entries are ``ArtifactType`` values and/or complex types
(``MessageSequence``, ``MessageSequenceOrdered``).

``outputs`` lists the ``BaseChunk`` subclasses the model is designed to
yield.

``tag_overrides`` lets a definition swap the global default
``TagSpec`` for one or more ``TagType`` values when this model emits
non-default delimiter strings.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any, Dict, List, Optional, Type

from ..data.chunks import BaseChunk, TextChunk
from ..enums.data import ArtifactType
from ..parser.types import TagSpec, TagType


def default_inputs() -> List[Any]:
  """Default chat contract: text artifacts shaped as a message sequence."""
  from ..data.models.conversation.message_sequence import MessageSequence
  return [ArtifactType.TEXT, MessageSequence]


def default_outputs() -> List[Type[BaseChunk]]:
  """Default chat contract: streamed text chunks."""
  return [TextChunk]


@dataclass
class ModelDefinition:
  """Metadata describing a single model.

  ``inputs`` lists what the model accepts after ``to_model_inputs``:
  ``ArtifactType`` values and optional complex types
  (``MessageSequence`` / ``MessageSequenceOrdered``).

  ``outputs`` lists the chunk classes the model is designed to yield.
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
  inputs: List[Any] = field(default_factory=default_inputs)
  outputs: List[Type[BaseChunk]] = field(default_factory=default_outputs)
  tag_overrides: Optional[Dict[TagType, TagSpec]] = None

  def artifact_types(self) -> List[ArtifactType]:
    """ArtifactType entries from ``inputs``."""
    return [x for x in (self.inputs or []) if isinstance(x, ArtifactType)]

  def chunk_types(self) -> List[Type[BaseChunk]]:
    """Chunk classes listed in ``outputs``."""
    return [
      x for x in (self.outputs or [])
      if isinstance(x, type) and issubclass(x, BaseChunk)
    ]

  def sequence_class(self) -> Optional[Type]:
    """Preferred message-sequence class, if any.

    ``MessageSequenceOrdered`` wins when both sequence types are listed.
    """
    from ..data.models.conversation.message_sequence import (
      MessageSequence,
      MessageSequenceOrdered,
    )
    inputs = self.inputs or []
    if MessageSequenceOrdered in inputs:
      return MessageSequenceOrdered
    if MessageSequence in inputs:
      return MessageSequence
    return None


########################################################################
#                         DEFINITION MERGER                            #
########################################################################
_ORDERED_UNION_FIELDS = frozenset({
  "aliases",
  "deployments",
  "architectures",
  "capabilities",
  "inputs",
  "outputs",
})
_OVERLAY_DICT_FIELDS = frozenset({
  "identifiers",
  "tag_overrides",
})


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
    ``capabilities``, ``inputs``, ``outputs``): concatenate, dedupe, keep
    first-seen order.
  - Overlay dicts (``identifiers``, ``tag_overrides``): incoming wins
    per key. Tag overrides replace per ``TagType``; no deep-merge of
    individual ``TagSpec`` fields.
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
    else:
      values[f.name] = iv if iv is not None else ev
  return ModelDefinition(**values)
