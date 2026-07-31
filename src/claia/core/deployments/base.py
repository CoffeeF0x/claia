"""
Abstract base class for deployment plugins.

A deployment knows how to take an architecture's model class plus a
conversation, flatten it to artifacts, and produce a stream of
``BaseChunk`` items (content only). Status lives on ``ModelResponse``.
"""

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, Iterator, Type

from ..data import Conversation
from ..data.chunks import BaseChunk
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
  ) -> Iterator[BaseChunk]:
    """
    Deploy (if needed) and run inference on a model.

    Yields ``BaseChunk`` content items as they arrive. Completion and
    errors are carried by the model's ``ModelResponse`` (generator
    return value), not by control chunks.

    Kwargs are split by ``ParamSpec`` scope at the framework boundary
    (``Registry._run_stream``) and handed in as two dicts:

    - ``init_kwargs`` — INIT-scoped kwargs for model construction
    - ``runtime_kwargs`` — RUNTIME-scoped kwargs for ``model.generate``

    Errors are raised as exceptions (typically ``DeploymentError``).
    """
