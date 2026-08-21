"""
Abstract base class for architecture plugins.

An architecture describes a family of models that share a common
implementation strategy (e.g., the OpenAI Chat Completions wire format,
the Anthropic Messages API, a local Hugging Face transformers pipeline).
The ABC is what consumers of ``claia.core`` (without the framework)
implement to ship a usable architecture.

Subclasses declare their metadata via a class-level ``info`` attribute
(an ``ArchitectureInfo`` instance). The default ``get_architecture_info``
simply returns that attribute, which lets the framework discover plugin
metadata without having to instantiate the class — a precondition for
the lazy two-phase plugin loading in ``claia.framework.manager``.
"""

from abc import ABC, abstractmethod
from typing import ClassVar, Type

from ..plugins.base import ArchitectureInfo


class BaseArchitecture(ABC):
  """Contract for architecture plugins."""

  info: ClassVar[ArchitectureInfo]

  def get_architecture_info(self) -> ArchitectureInfo:
    """Return metadata describing this architecture.

    Default implementation returns the class-level ``info`` attribute.
    Subclasses may override if they need to compute the info object on
    demand, but in that case they pay the cost of an instantiation at
    discovery time.
    """
    return type(self).info

  @abstractmethod
  def get_model_class(self) -> Type:
    """Return the concrete model class implemented by this architecture."""
