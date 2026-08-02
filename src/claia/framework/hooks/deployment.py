"""
Pluggy hookspecs for deployment plugins.

These specs mirror ``BaseDeployment`` in ``claia.core.deployments.base``.
"""

import pluggy
from typing import Any, Dict, Iterator, Optional, Type

from ...core.data import Conversation
from ...core.data.chunks import BaseChunk
from ...core.definitions.model_definition import ModelDefinition
from ...core.plugins.base import DeploymentInfo


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
    init_kwargs: Dict[str, Any],
    runtime_kwargs: Dict[str, Any],
    definition: Optional[ModelDefinition] = None,
  ) -> Iterator[BaseChunk]:
    """Deploy (if needed) and yield ``BaseChunk`` items from the model.

    Default implementation lives on ``BaseDeployment.run``. Subclasses
    typically only override ``create_model``. ``init_kwargs`` feed the
    model constructor; ``runtime_kwargs`` feed ``model.generate``.
    ``definition`` supplies ``supported_inputs`` for translation.
    """


__all__ = ["DeploymentHooks", "DeploymentInfo"]
