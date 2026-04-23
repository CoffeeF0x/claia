"""
Abstract base class for deployment plugins.

A deployment knows how to take an architecture's model class plus a
conversation and produce a stream of ``GenerationChunk`` items.
Concrete deployments handle caching of model instances themselves; the
framework only provides a shared ``cache`` dict.

The framework's ``claia_deployments`` hookspec mirrors this ABC.
Subclasses declare their metadata via a class-level ``info`` attribute
so plugin discovery does not have to instantiate the plugin.
"""

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, Iterator, Type

from ..data import Conversation
from ..modality import GenerationChunk
from ..plugins.base import DeploymentInfo


class BaseDeployment(ABC):
  """Contract for deployment plugins."""

  info: ClassVar[DeploymentInfo]

  def get_deployment_info(self) -> DeploymentInfo:
    """Return metadata describing this deployment method.

    Default implementation returns the class-level ``info`` attribute.
    """
    return type(self).info

  @abstractmethod
  def run(
    self,
    model_name: str,
    model_class: Type,
    conversation: Conversation,
    cache: Dict[str, Any],
    init_kwargs: Dict[str, Any],
    runtime_kwargs: Dict[str, Any],
  ) -> Iterator[GenerationChunk]:
    """
    Deploy (if needed) and run inference on a model.

    Yields ``GenerationChunk`` items as they arrive from the underlying
    model. Text-only deployments wrap each token in a
    ``ChunkKind.TEXT`` chunk; multi-modal deployments may emit image,
    audio, video or progress chunks.

    Kwargs are split by ``ParamSpec`` scope at the framework boundary
    (``Registry._run_stream``) and handed in as two dicts so each one
    reaches the layer that actually consumes it:

    - ``init_kwargs`` — INIT-scoped kwargs (credentials, endpoints,
      paths). Forwarded to the model class constructor when a fresh
      instance is built.
    - ``runtime_kwargs`` — RUNTIME-scoped kwargs (``temperature``,
      ``max_tokens``, ...) already resolved against the architecture's
      spec defaults. Forwarded to ``model.generate`` per call.

    Errors are raised as exceptions (typically ``DeploymentError``).
    """
