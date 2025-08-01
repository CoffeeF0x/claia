"""
Default deployment solver plugin.

This solver provides basic deployment decision logic when no specific
solver is requested or when other solvers cannot handle a request.
"""

import logging
from typing import Optional, Dict, List, Any

# Internal dependencies
from common.results import Result
from ..hooks.solver import SolverInfo, DeploymentParams


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
      description="Basic deployment decision logic with sensible defaults"
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
    cache: Dict[str, Any],
    deployment_preference: Optional[str] = None,
    deployment_method: Optional[str] = None,
    **kwargs
  ) -> Result[DeploymentParams]:
    """
    Determine the best deployment method for the request.
    """
    try:
      logger.debug(f"Default solver processing: {model_name}")

      # Step 1: Resolve model name to canonical form
      canonical_model_name = self._resolve_model_name(model_name, available_models)
      if canonical_model_name != model_name:
        logger.debug(f"Resolved '{model_name}' to '{canonical_model_name}'")
        model_name = canonical_model_name

      # Step 2: Validate model exists
      if model_name not in available_models:
        return Result.fail(f"Model '{model_name}' not found in supported models")

      # Step 3: If deployment method is forced, use it
      if deployment_method:
        if deployment_method in available_deployments:
          return Result(data=DeploymentParams(
            deployment_name=deployment_method,
            model_name=model_name
          ))
        else:
          return Result.fail(f"Forced deployment method '{deployment_method}' not available")

      # Step 4: Determine model type and choose deployment
      model_type = self._determine_model_type(model_name, available_models)
      chosen_deployment = self._choose_deployment(
        model_name,
        model_type,
        available_deployments,
        deployment_preference
      )

      if not chosen_deployment:
        return Result.fail(f"No suitable deployment method found for {model_name}")

      return Result(data=DeploymentParams(
        deployment_name=chosen_deployment,
        model_name=model_name
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

    # Return original if not found
    logger.debug(f"No resolution found for '{model_name}'")
    return model_name
