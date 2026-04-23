"""
ModelDefinition dataclass.

A ``ModelDefinition`` is pure metadata about a model — its display title,
aliases, supported deployments and architectures, capabilities, and
input/output modalities. It does not implement model behaviour; that
lives in the corresponding architecture plugin.

Definition plugins return a dict of ``{model_name: ModelDefinition}``
which the framework merges across all installed providers.

Modality fields default to text-in / text-out so existing plain-text
definitions keep working unchanged. Multi-modal providers extend the
lists.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..modality import Modality


@dataclass
class ModelDefinition:
  """Metadata describing a single model.

  Most fields default to ``None`` so that providers can contribute
  partial definitions; the framework merges definitions across
  providers, preferring later non-None values.

  ``input_modalities`` / ``output_modalities`` are first-class fields
  so applications can filter or route models by what they accept and
  produce without re-parsing the free-form ``capabilities`` strings.
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
