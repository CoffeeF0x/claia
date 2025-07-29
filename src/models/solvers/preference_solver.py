"""
Preference-based deployment solver plugin.

This solver provides more intelligent deployment decisions based on
user preferences, model characteristics, and system constraints.
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
class PreferenceSolverPlugin:
  """
  Preference-based solver plugin for intelligent deployment decisions.

  This solver implements more sophisticated logic:
  1. Analyzes user preferences and constraints
  2. Considers model characteristics and requirements
  3. Balances performance, cost, and availability
  """

  def get_solver_info(self) -> SolverInfo:
    """Get information about this solver."""
    return SolverInfo(
      name="preference",
      title="Preference Solver",
      description="Intelligent deployment decisions based on preferences and constraints",
      priority=50  # Higher priority than default
    )

  def can_solve(self, model_name: str, deployment_preference: Optional[str] = None, **kwargs) -> bool:
    """Check if this solver can handle the request."""
    # This solver can handle any request, but prefers when preferences are specified
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
    Determine the best deployment method for the request using preferences.
    """
    try:
      logger.debug(f"Preference solver processing: {model_name}")

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

      # Determine model type and characteristics
      model_type = self._determine_model_type(model_name, available_models)
      model_info = available_models.get(model_name, {})

      # Score each available deployment method
      deployment_scores = self._score_deployments(
        model_name,
        model_type,
        model_info,
        available_deployments,
        deployment_preference,
        kwargs
      )

      if not deployment_scores:
        return Result.fail(f"No suitable deployment method found for {model_name}")

      # Choose highest scoring deployment
      best_deployment = max(deployment_scores.items(), key=lambda x: x[1])
      chosen_deployment, confidence = best_deployment

      return Result(data=DeploymentDecision(
        deployment_method=chosen_deployment,
        model_name=model_name,
        model_type=model_type,
        deployment_params=self._build_deployment_params(kwargs),
        confidence=confidence
      ))

    except Exception as e:
      logger.error(f"Error in preference solver: {str(e)}")
      return Result.fail(f"Solver error: {str(e)}")

  def _determine_model_type(self, model_name: str, available_models: Dict[str, Any]) -> str:
    """Determine the type of model based on its name and characteristics."""
    if model_name not in available_models:
      return "unknown"

    model_info = available_models[model_name]

    # Check if it's an API model (common API model patterns)
    api_models = ['gpt', 'claude', 'gemini', 'palm', 'openai', 'anthropic']
    if any(api_name in model_name.lower() for api_name in api_models):
      return "api"

    # Check if it's a transformer model
    transformer_models = ['llama', 'mistral', 'phi', 'qwen', 'gemma', 'falcon', 'alpaca']
    if any(transformer in model_name.lower() for transformer in transformer_models):
      return "transformers"

    # Check model info for hints
    if hasattr(model_info, 'capabilities'):
      # Could analyze capabilities to determine type
      pass

    # Default assumption
    return "transformers"

  def _score_deployments(
    self,
    model_name: str,
    model_type: str,
    model_info: Dict[str, Any],
    available_deployments: List[str],
    deployment_preference: Optional[str],
    kwargs: Dict[str, Any]
  ) -> Dict[str, float]:
    """Score each deployment method based on preferences and constraints."""
    scores = {}

    for deployment in available_deployments:
      score = self._score_single_deployment(
        deployment,
        model_name,
        model_type,
        model_info,
        deployment_preference,
        kwargs
      )
      if score > 0:
        scores[deployment] = score

    return scores

  def _score_single_deployment(
    self,
    deployment: str,
    model_name: str,
    model_type: str,
    model_info: Dict[str, Any],
    deployment_preference: Optional[str],
    kwargs: Dict[str, Any]
  ) -> float:
    """Score a single deployment method."""
    score = 0.0

    # Base compatibility score
    if model_type == "api" and deployment == "api":
      score += 0.8
    elif model_type == "transformers" and deployment == "local":
      score += 0.8
    elif deployment == "remote":
      score += 0.6  # Remote can handle most things

    # Preference bonus
    if deployment_preference:
      if deployment_preference == deployment:
        score += 0.3
      elif deployment_preference in ["fast", "quick"] and deployment == "api":
        score += 0.2
      elif deployment_preference in ["local", "private"] and deployment == "local":
        score += 0.2
      elif deployment_preference in ["cloud", "scalable"] and deployment == "remote":
        score += 0.2

    # Resource constraints
    device = kwargs.get('device')
    if device:
      if device.lower() == 'cpu' and deployment == "local":
        score += 0.1
      elif device.lower().startswith('cuda') and deployment == "local":
        score += 0.2

    # API key availability
    api_key = kwargs.get('api_key') or kwargs.get('openai_api_key') or kwargs.get('anthropic_api_key')
    if deployment == "api":
      if api_key:
        score += 0.1
      else:
        score -= 0.3  # Penalize API deployment without API key

    # Cost considerations (API calls cost money, local doesn't)
    cost_preference = kwargs.get('cost_preference', 'balanced')
    if cost_preference == 'low' and deployment == "local":
      score += 0.1
    elif cost_preference == 'high' and deployment == "api":
      score += 0.1

    return max(0.0, min(1.0, score))  # Clamp between 0 and 1

  def _build_deployment_params(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Build deployment parameters from the provided kwargs."""
    # Pass through all kwargs as deployment parameters
    # The deployment method will decide what to use
    return dict(kwargs)
