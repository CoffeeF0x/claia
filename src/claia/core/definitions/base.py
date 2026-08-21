"""
Abstract base class for definition providers.

A definition provider returns a dict of ``{model_name: ModelDefinition}``
contributing model metadata to the registry.
"""

from abc import ABC, abstractmethod
from typing import ClassVar, Dict

from ..plugins.base import DefinitionsInfo
from .model_definition import ModelDefinition


class BaseDefinitionProvider(ABC):
  """Contract for definition providers."""

  info: ClassVar[DefinitionsInfo]

  @abstractmethod
  def get_definitions(self) -> Dict[str, ModelDefinition]:
    """Return the model definitions contributed by this provider."""
