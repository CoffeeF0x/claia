"""
Abstract base class for nodes.

A node is a place compute lives. It hosts deployments: given a
resolved pairing from the solver it reuses or provisions a deployed
architecture instance, then streams the generate contract back
(chunks up, ``ModelResponse`` terminal). Instance lifecycle — reuse,
unload, stats — lives here, behind a stable interface that remote
hosts implement by speaking the same contract over a wire.
"""

from __future__ import annotations

import logging
from abc import ABC
from typing import Any, ClassVar, Dict, Optional, Tuple, Type

from ..data.response import GenerateStream
from ..deployments.base import BaseDeployment, ModelInputs
from ..plugins.base import NodeInfo


logger = logging.getLogger(__name__)


class BaseNode(ABC):
  """Contract and shared instance-lifecycle path for nodes."""

  info: ClassVar[NodeInfo]

  #: True when the node hosts compute off this machine. The solver's
  #: ``deployment_preference`` filter reads this.
  remote: ClassVar[bool] = False

  def __init__(self):
    # instance key -> (owning deployment, deployed architecture instance)
    self._instances: Dict[str, Tuple[BaseDeployment, Any]] = {}

  # ------------------------------------------------------------------
  # Lifecycle
  # ------------------------------------------------------------------
  def start(self) -> None:
    """Open connections/resources. Default: nothing to do."""
    pass

  def stop(self) -> None:
    """Tear down every hosted instance and release resources."""
    self.unload()

  # ------------------------------------------------------------------
  # Serving
  # ------------------------------------------------------------------
  def run(
    self,
    deployment: BaseDeployment,
    architecture_class: Type,
    model_name: str,
    inputs: ModelInputs,
    init_kwargs: Dict[str, Any],
    runtime_kwargs: Dict[str, Any],
  ) -> GenerateStream:
    """Serve one generate call: reuse or provision, then stream.

    Returns a ``GenerateStream`` — iterate it for chunks, read
    ``.response`` after exhaustion for the terminal ``ModelResponse``.
    """
    instance = self._resolve_instance(
      deployment, architecture_class, model_name, init_kwargs
    )
    return GenerateStream(deployment.run(instance, inputs, runtime_kwargs))

  @staticmethod
  def instance_key(model_name: str, deployment_name: str, architecture_name: str) -> str:
    """Key identifying one deployed instance on this node."""
    return f"{model_name}:{deployment_name}:{architecture_name}"

  def _resolve_instance(
    self,
    deployment: BaseDeployment,
    architecture_class: Type,
    model_name: str,
    init_kwargs: Dict[str, Any],
  ) -> Any:
    """Return a hosted instance, deploying one if none is cached."""
    architecture_name = getattr(getattr(architecture_class, "info", None), "name", architecture_class.__name__)
    key = self.instance_key(model_name, deployment.info.name, architecture_name)
    if key in self._instances:
      logger.debug(f"Reusing deployed instance {key} on node {self.info.name}")
      return self._instances[key][1]

    logger.debug(f"Deploying {key} on node {self.info.name}")
    instance = deployment.deploy(architecture_class, model_name, init_kwargs)
    self._instances[key] = (deployment, instance)
    return instance

  # ------------------------------------------------------------------
  # Instance lifecycle surface
  # ------------------------------------------------------------------
  def loaded(self) -> Dict[str, str]:
    """Map of instance key -> architecture class name for hosted instances."""
    return {key: type(inst).__name__ for key, (_dep, inst) in self._instances.items()}

  def stats(self) -> Dict[str, Any]:
    """Statistics about hosted instances."""
    return {
      "total_models": len(self._instances),
      "cached_models": list(self._instances.keys()),
    }

  def unload(
    self,
    model_name: Optional[str] = None,
    deployment_name: Optional[str] = None,
  ) -> int:
    """Tear down hosted instances matching the given filters.

    With no arguments, unloads everything. Returns the number of
    instances removed. Teardown errors are logged and swallowed —
    the instance is dropped either way.
    """
    removed = 0
    for key in list(self._instances):
      k_model, k_deployment, _k_arch = key.rsplit(":", 2)
      if model_name is not None and k_model != model_name:
        continue
      if deployment_name is not None and k_deployment != deployment_name:
        continue

      deployment, instance = self._instances.pop(key)
      try:
        deployment.teardown(instance)
      except Exception as e:
        logger.warning(f"Teardown of {key} raised {e}; instance dropped anyway")
      removed += 1
      logger.debug(f"Unloaded {key} from node {self.info.name}")
    return removed
