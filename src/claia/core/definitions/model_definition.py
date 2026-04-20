"""
ModelDefinition dataclass.

A ``ModelDefinition`` is pure metadata about a model — its display title,
aliases, supported deployments and architectures, capabilities, etc. It
does not implement model behaviour; that lives in the corresponding
architecture plugin.

Definition plugins return a dict of ``{model_name: ModelDefinition}``
which the framework merges across all installed providers.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ModelDefinition:
  """Metadata describing a single model.

  Fields default to ``None`` so that providers can contribute partial
  definitions; the framework merges definitions across providers,
  preferring later non-None values.
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
