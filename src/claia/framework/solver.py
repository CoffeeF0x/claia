"""
Serving-stack solver.

Turns a model name into a pairing: definition, architecture class,
deployment, and node. The registry owns one instance; it is not a
plugin group.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..core.data.chunks import ToolChunk
from ..core.enums.deployment import DeploymentPreference
from ..core.plugins.base import ServingPlan
from ..core.results import ResolveError


logger = logging.getLogger(__name__)


########################################################################
#                             SOLVER RESULT                            #
########################################################################
@dataclass
class SolverResult:
  """Resolved serving pairing for one model call."""
  plan: ServingPlan
  definition: Any
  architecture_class: Any
  deployment: Any
  node: Any

  @property
  def supports_native_tools(self) -> bool:
    """True when the definition lists ``ToolChunk`` in ``outputs``."""
    if self.definition is None:
      return False
    return ToolChunk in self.definition.chunk_types()


########################################################################
#                                SOLVER                                #
########################################################################
class Solver:
  """Solve a model request into a ``SolverResult``.

  Resolution: name/alias -> definition -> first installed
  architecture -> its linked deployment -> a node allowed by
  ``deployment_preference``. See ``DeploymentPreference``.

  Failures raise ``ResolveError``.
  """

  def __init__(self, manager):
    self.manager = manager

  @staticmethod
  def resolve_model_name(model_name: str, available_models: Dict[str, Any]) -> Optional[str]:
    """Resolve a model name or alias to its canonical name."""
    if model_name in available_models:
      return model_name

    for canonical_name, model_info in available_models.items():
      aliases = getattr(model_info, "aliases", None)
      if aliases and model_name in aliases:
        logger.debug(f"Resolved alias '{model_name}' to '{canonical_name}'")
        return canonical_name

    logger.debug(f"No resolution found for '{model_name}'")
    return None

  @staticmethod
  def coerce_preference(value) -> DeploymentPreference:
    """Accept a ``DeploymentPreference``, its value string, or ``None``."""
    if value is None:
      return DeploymentPreference.ANY
    if isinstance(value, DeploymentPreference):
      return value
    try:
      return DeploymentPreference(value)
    except ValueError:
      expected = ", ".join(p.value for p in DeploymentPreference)
      raise ResolveError(
        f"Unknown deployment_preference '{value}' "
        f"(expected one of {expected})"
      )

  def solve(
    self,
    model_name: str,
    deployment_preference=DeploymentPreference.ANY,
  ) -> SolverResult:
    """Solve ``model_name`` into a serving pairing."""
    deployment_preference = self.coerce_preference(deployment_preference)

    definitions = self.manager.get_supported_models()
    resolved_name = self.resolve_model_name(model_name, definitions)
    if not resolved_name:
      raise ResolveError(f"Model '{model_name}' not found")
    definition = definitions[resolved_name]

    candidates = getattr(definition, "architectures", None) or []
    if not candidates:
      raise ResolveError(f"No architecture specified for model '{resolved_name}'")

    rejected: List[str] = []
    for architecture_name in candidates:
      architecture_class = self.manager.get_architecture_class(architecture_name)
      if architecture_class is None:
        rejected.append(f"{architecture_name}: not installed")
        continue

      deployment_name = getattr(architecture_class, "deployment", "")
      deployment = (
        self.manager.get_deployment_plugin(deployment_name) if deployment_name else None
      )
      if deployment is None:
        rejected.append(
          f"{architecture_name}: deployment '{deployment_name}' unavailable"
        )
        continue

      if deployment.api and deployment_preference is not DeploymentPreference.ANY:
        rejected.append(
          f"{architecture_name}: api deployment excluded by "
          f"preference '{deployment_preference.value}'"
        )
        continue

      node = self._pick_node(deployment_preference)
      if node is None:
        rejected.append(
          f"{architecture_name}: no node allowed by preference "
          f"'{deployment_preference.value}'"
        )
        continue

      provider_model_name = resolved_name
      identifiers = getattr(definition, "identifiers", None) or {}
      if architecture_name in identifiers:
        provider_model_name = identifiers[architecture_name]

      plan = ServingPlan(
        model_name=resolved_name,
        provider_model_name=provider_model_name,
        architecture_name=architecture_name,
        deployment_name=deployment_name,
        node_name=node.info.name,
      )
      return SolverResult(
        plan=plan,
        definition=definition,
        architecture_class=architecture_class,
        deployment=deployment,
        node=node,
      )

    detail = "; ".join(rejected)
    raise ResolveError(f"No serving pairing for model '{resolved_name}': {detail}")

  def _pick_node(self, deployment_preference: DeploymentPreference):
    """Return the first node allowed by the preference, or ``None``."""
    for node in self.manager.iter_node_instances():
      if node.remote and deployment_preference is DeploymentPreference.LOCAL_ONLY:
        continue
      return node
    return None
