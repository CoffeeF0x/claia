"""
Abstract base class for deployment plugins.

A deployment knows how to take an architecture's model class plus a
conversation and produce a stream of tokens. Concrete deployments handle
caching of model instances themselves; the framework only provides a
shared ``cache`` dict.

The framework's ``claia_deployments`` hookspec mirrors this ABC.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator, Type

from ..data import Conversation
from ..plugins.base import DeploymentInfo


class BaseDeployment(ABC):
  """Contract for deployment plugins."""

  @abstractmethod
  def get_deployment_info(self) -> DeploymentInfo:
    """Return metadata describing this deployment method."""

  @abstractmethod
  def run(
    self,
    model_name: str,
    model_class: Type,
    conversation: Conversation,
    cache: Dict[str, Any],
    **kwargs,
  ) -> Iterator[str]:
    """
    Deploy (if needed) and run inference on a model.

    Yields tokens as they arrive from the underlying model. Errors are
    raised as exceptions (typically ``DeploymentError``).
    """
