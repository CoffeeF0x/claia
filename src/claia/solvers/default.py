"""
Default deployment solver plugin.

This solver provides basic deployment decision logic when no specific
solver is requested or when other solvers cannot handle a request.
"""

import logging
import pluggy
from typing import Optional, Dict, List, Any

# Internal dependencies
from claia.lib.results import Result
from ..hooks.solver import SolverInfo, DeploymentParams
from ..hooks.definition import ModelDefinition



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)
hookimpl = pluggy.HookimplMarker("claia_solvers")



########################################################################
#                               CLASSES                                #
########################################################################
class DefaultSolverPlugin:
  """
  Default solver plugin for basic deployment decisions.
  """

  @hookimpl
  def get_solver_info(self) -> SolverInfo:
    """Get information about this solver."""
    return SolverInfo(
      name="default",
      title="Default Solver",
      description="Basic deployment decision logic with sensible defaults"
    )

  @hookimpl
  def can_solve(self, model_name: str, deployment_preference: Optional[str] = None, **kwargs) -> bool:
    """Check if this solver can handle the request."""
    return True

  @hookimpl
  def solve_deployment(
    self,
    model_name: str,
    available_deployments: List[str],
    available_models: Dict[str, Any],
    cache: Dict[str, Any],
    deployment_preference: Optional[str] = None,
    deployment_method: Optional[str] = None,
    **kwargs
  ) -> Result:
    """
    Determine the best deployment method for the request.
    """
    try:
      logger.debug(f"Default solver processing: {model_name}")

      # Resolve model name
      resolved_model_name = self._resolve_model_name(model_name, available_models)
      if not resolved_model_name:
        return Result.fail(f"Model '{model_name}' not found")

      # Get model info
      model_info: ModelDefinition = available_models.get(resolved_model_name)
      if not model_info:
        return Result.fail(f"Model '{resolved_model_name}' not found")

      # Resolve deployment method (treat as list)
      deployments = model_info.deployments or []
      if deployment_method and deployment_method not in available_deployments:
        return Result.fail(f"Deployment method '{deployment_method}' is not available.")
      if deployment_method and deployment_method not in deployments:
        return Result.fail(f"Deployment method '{deployment_method}' is not available for model '{resolved_model_name}'.")
      if not deployments:
        return Result.fail(f"No deployment methods available for model '{resolved_model_name}'.")
      resolved_deployment_method = deployment_method or deployments[0]

      # Resolve architecture name from definitions (first if multiple)
      architectures = model_info.architectures or []
      if not architectures:
        return Result.fail(f"No architecture specified for model '{resolved_model_name}'.")
      architecture_name = architectures[0]

      if resolved_deployment_method and architecture_name:
        return Result(data=DeploymentParams(
          deployment_name=resolved_deployment_method,
          model_name=resolved_model_name,
          architecture_name=architecture_name
        ))
      else:
        return Result.fail(f"No suitable deployment method found for {model_name}")

    except Exception as e:
      logger.error(f"Error in default solver: {str(e)}")
      return Result.fail(f"Solver error: {str(e)}")

  def _resolve_model_name(self, model_name: str, available_models: Dict[str, Any]) -> str:
    """Resolve a model name or alias to its canonical name."""
    # Check if it's already a canonical name
    if model_name in available_models:
      return model_name

    # Check aliases
    for canonical_name, model_info in available_models.items():
      if hasattr(model_info, 'aliases') and model_info.aliases and model_name in model_info.aliases:
        logger.debug(f"Resolved alias '{model_name}' to '{canonical_name}'")
        return canonical_name

    # Return None if not found
    logger.debug(f"No resolution found for '{model_name}'")
    return None
