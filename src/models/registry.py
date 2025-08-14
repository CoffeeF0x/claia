"""Manage models in the CLAIA application.

This module provides a ModelRegistry that follows the deployment architecture:
Registry -> Solver -> Deployment Method -> Model
"""

import logging
from typing import Any, Optional, Dict

# Internal dependencies
from common.results import Result
from common.files.conversation import Conversation
from .manager import ModuleManager


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                            MODEL REGISTRY                            #
########################################################################
class ModelRegistry:
  """
  Manages models in the CLAIA application.

  This registry follows the deployment architecture:
  Registry -> Solver -> Deployment Method -> Model

  The registry initializes a cache and loads all modules, then delegates
  deployment decisions to solvers, which call appropriate deployment methods.
  """
  def __init__(self):
    """Initialize the ModelRegistry."""
    logger.debug("Initializing Model Registry")

    # Initialize module manager and model cache
    self.manager = ModuleManager()
    self.cache = {}  # Cache for loaded models

    # Load all plugins
    self.manager.load_all_plugins()

    logger.info("ModelRegistry initialized successfully")

  def run(
    self,
    model_name: str,
    conversation: Conversation,
    solver: Optional[str] = None,
    deployment_method: Optional[str] = None,
    deployment_preference: Optional[str] = None,
    **kwargs
  ) -> Result:
    """
    Pass the request to the solver for processing.

    Args:
      model_name: Name or alias of the model
      conversation: Conversation to process
      solver: Optional specific solver to use
      deployment_method: Optional forced deployment method
      deployment_preference: Optional deployment preference string
      **kwargs: Additional parameters (API keys, device, etc.)

    Returns:
      Result containing the generated response
    """
    try:
      logger.debug(f"Running model {model_name}")

      # Get available models and deployments
      available_models = self.manager.get_supported_models()
      available_deployments = list(self.manager.get_available_deployments().keys())

      # Get solver plugin
      selected_solver = self.manager.get_solver_plugin(solver)
      if not selected_solver:
        return Result.fail(f"No solver available (requested: {solver})")

      # Call solver to determine deployment
      params_result = selected_solver.solve_deployment(
        model_name=model_name,
        available_deployments=available_deployments,
        available_models=available_models,
        cache=self.cache,
        deployment_preference=deployment_preference,
        deployment_method=deployment_method,
        **kwargs
      )

      if params_result.is_error():
        return params_result

      deployment_params = params_result.data
      logger.debug(f"Solver result: {deployment_params.deployment_name} for {deployment_params.model_name}")

      # Resolve model class from architecture plugins
      model_class = self.manager.get_model_class(deployment_params.model_name)
      if not model_class:
        return Result.fail(f"No architecture found for model '{deployment_params.model_name}'")

      # Get deployment plugin
      selected_deployment = self.manager.get_deployment_plugin(deployment_params.deployment_name)
      if not selected_deployment:
        return Result.fail(f"Deployment method '{deployment_params.deployment_name}' not available")

      # Let deployment plugin handle deployment + inference
      result = selected_deployment.run(
        model_name=deployment_params.model_name,
        model_class=model_class,
        conversation=conversation,
        cache=self.cache,
        **kwargs
      )

      return result

    except Exception as e:
      logger.error(f"Error running model {model_name}: {str(e)}")
      return Result.fail(f"Failed to run model: {str(e)}")

  def get_supported_models(self) -> Dict[str, Any]:
    """
    Get all models supported by registered plugins.

    Returns:
        Dict mapping model names to model information
    """
    return self.manager.get_supported_models()

  def get_available_deployments(self) -> Dict[str, Any]:
    """
    Get all available deployment methods.

    Returns:
        Dict mapping deployment names to deployment information
    """
    return self.manager.get_available_deployments()

  def get_available_solvers(self) -> Dict[str, Any]:
    """
    Get all available deployment solvers.

    Returns:
        Dict mapping solver names to solver information
    """
    return self.manager.get_available_solvers()

  def get_loaded_models(self) -> Dict[str, Any]:
    """Get dictionary of currently loaded models."""
    return {key: type(model).__name__ for key, model in self.cache.items()}

  def unload_model(self, model_name: str, deployment_method: str = None) -> Result:
    """Unload a model from cache."""
    try:
      if deployment_method:
        cache_key = f"{model_name}:{deployment_method}"
        if cache_key in self.cache:
          del self.cache[cache_key]
          logger.debug(f"Unloaded model {cache_key}")
      else:
        # Remove all instances of this model
        keys_to_remove = [key for key in self.cache.keys() if key.startswith(f"{model_name}:")]
        for key in keys_to_remove:
          del self.cache[key]
          logger.debug(f"Unloaded model {key}")

      return Result(data="Model unloaded successfully")
    except Exception as e:
      return Result.fail(f"Failed to unload model: {str(e)}")

  def unload_all_models(self) -> Result:
    """Unload all models from cache."""
    try:
      self.cache.clear()
      logger.debug("Unloaded all models")
      return Result(data="All models unloaded successfully")
    except Exception as e:
      return Result.fail(f"Failed to unload all models: {str(e)}")

  def get_cache_stats(self) -> Dict[str, Any]:
    """Get statistics about the model cache."""
    return {
      "total_models": len(self.cache),
      "cached_models": list(self.cache.keys())
    }
