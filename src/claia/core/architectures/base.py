"""
Abstract base class for architecture plugins.

An architecture describes a family of models that share a common
implementation strategy (e.g., the OpenAI Chat Completions wire format,
the Anthropic Messages API, a local Hugging Face transformers pipeline).
The framework's ``claia_architectures`` hookspec mirrors this ABC; the
ABC itself is what consumers of ``claia.core`` (without the framework)
implement to ship a usable architecture.
"""

from abc import ABC, abstractmethod
from typing import Type

from ..plugins.base import ArchitectureInfo


class BaseArchitecture(ABC):
  """Contract for architecture plugins."""

  @abstractmethod
  def get_architecture_info(self) -> ArchitectureInfo:
    """Return metadata describing this architecture."""

  @abstractmethod
  def get_model_class(self) -> Type:
    """Return the concrete model class implemented by this architecture."""
