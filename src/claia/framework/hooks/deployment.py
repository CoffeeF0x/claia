"""
Pluggy hookspecs for deployment plugins.

These specs mirror ``BaseDeployment`` in ``claia.core.deployments.base``.
"""

import pluggy
from typing import Any, Dict, Iterator, Type

from claia.core.data import Conversation
from claia.core.plugins.base import DeploymentInfo


hookspec = pluggy.HookspecMarker("claia_deployments")


class DeploymentHooks:
  """Hook specifications for deployment plugins."""

  @hookspec
  def get_deployment_info(self) -> DeploymentInfo:
    """Return metadata describing this deployment method."""

  @hookspec
  def run(
    self,
    model_name: str,
    model_class: Type,
    conversation: Conversation,
    cache: Dict[str, Any],
    **kwargs,
  ) -> Iterator[str]:
    """Deploy (if needed) and yield tokens from the model."""


__all__ = ["DeploymentHooks", "DeploymentInfo"]
