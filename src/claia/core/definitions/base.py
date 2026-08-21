"""
Abstract base class for definition-provider plugins.

A definition provider returns a dict of ``{model_name: ModelDefinition}``
contributing model metadata to the registry.
"""

from abc import ABC, abstractmethod
from typing import Dict

from .model_definition import ModelDefinition


class BaseDefinitionProvider(ABC):
  """Contract for definition-provider plugins."""

  @abstractmethod
  def get_definitions(self) -> Dict[str, ModelDefinition]:
    """Return the model definitions contributed by this provider."""
