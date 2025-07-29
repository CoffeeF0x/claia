"""
Default deployment solver plugin.

This solver provides basic deployment decision logic when no specific
solver is requested or when other solvers cannot handle a request.
"""

import logging
from typing import Optional, Dict, List, Any

# Internal dependencies
from common.results import Result
from ..hooks.solver_hooks import SolverInfo, DeploymentDecision


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                               CLASSES                                #
########################################################################
class DefaultSolverPlugin:
  """
  Default solver plugin for basic deployment decisions.

  This solver implements simple logic:
  1. Prefer API deployments for known API models
  2. Prefer local deployments for transformer models
  3. Fall back to remote deployments as needed
  """

  def get_solver_info(self) -> SolverInfo:
    """Get information about this solver."""
    return SolverInfo(
      name="default",
      title="Default Solver",
      description="Basic deployment decision logic with sensible defaults",
      priority=100  # Default priority
    )

  def can_solve(self, model_name: str, deployment_preference: Optional[str] = None, **kwargs) -> bool:
    """Check if this solver can handle the request."""
    # Default solver can handle any request as a fallback
    return True

  def solve_deployment(
    self,
    model_name: str,
    available_deployments: List[str],
    available_models: Dict[str, Any],
    deployment_preference: Optional[str] = None,
    deployment_method: Optional[str] = None,
    **kwargs
  ) -> Result[DeploymentDecision]:
    """
    Determine the best deployment method for the request.
    """
    try:
      logger.debug(f"Default solver processing: {model_name}")

      # If deployment method is forced, use it
      if deployment_method:
        if deployment_method in available_deployments:
          return Result(data=DeploymentDecision(
            deployment_method=deployment_method,
            model_name=model_name,
            model_type=self._determine_model_type(model_name, available_models),
            deployment_params=self._build_deployment_params(kwargs),
            confidence=1.0
          ))
        else:
          return Result.fail(f"Forced deployment method '{deployment_method}' not available")

      # Determine model type
      model_type = self._determine_model_type(model_name, available_models)

      # Apply deployment preference logic
      chosen_deployment = self._choose_deployment(
        model_name,
        model_type,
        available_deployments,
        deployment_preference
      )

      if not chosen_deployment:
        return Result.fail(f"No suitable deployment method found for {model_name}")

      return Result(data=DeploymentDecision(
        deployment_method=chosen_deployment,
        model_name=model_name,
        model_type=model_type,
        deployment_params=self._build_deployment_params(kwargs),
        confidence=0.8  # Moderate confidence for default logic
      ))

    except Exception as e:
      logger.error(f"Error in default solver: {str(e)}")
      return Result.fail(f"Solver error: {str(e)}")

  def _determine_model_type(self, model_name: str, available_models: Dict[str, Any]) -> str:
    """Determine the type of model based on its name and characteristics."""
    if model_name not in available_models:
      return "unknown"

    model_info = available_models[model_name]

    # Check if it's an API model (common API model patterns)
    api_models = ['gpt', 'claude', 'gemini', 'palm']
    if any(api_name in model_name.lower() for api_name in api_models):
      return "api"

    # Check if it's a transformer model
    transformer_models = ['llama', 'mistral', 'phi', 'qwen', 'gemma']
    if any(transformer in model_name.lower() for transformer in transformer_models):
      return "transformers"

    # Default based on capabilities or other info
    return "transformers"  # Default assumption

  def _choose_deployment(
    self,
    model_name: str,
    model_type: str,
    available_deployments: List[str],
    deployment_preference: Optional[str]
  ) -> Optional[str]:
    """Choose the best deployment method."""

    # Handle deployment preferences
    if deployment_preference:
      if deployment_preference == "api" and "api" in available_deployments:
        return "api"
      elif deployment_preference == "local" and "local" in available_deployments:
        return "local"
      elif deployment_preference == "remote" and "remote" in available_deployments:
        return "remote"
      elif deployment_preference in available_deployments:
        return deployment_preference

    # Default logic based on model type
    if model_type == "api":
      if "api" in available_deployments:
        return "api"
    elif model_type == "transformers":
      if "local" in available_deployments:
        return "local"

    # Fallback: choose first available deployment
    if available_deployments:
      return available_deployments[0]

    return None

  def _build_deployment_params(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Build deployment parameters from the provided kwargs."""
    # Pass through all kwargs as deployment parameters
    # The deployment method will decide what to use
    return dict(kwargs)
