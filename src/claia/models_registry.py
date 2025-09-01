"""Manage models in the CLAIA application.

This module provides a ModelRegistry that follows the deployment architecture:
Registry -> Solver -> Deployment Method -> Model
"""

import logging
from typing import Any, Optional, Dict

# Internal dependencies
from claia.lib.results import Result
from claia.lib.files.conversation import Conversation
from .manager import UnifiedManager


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
    self.manager = UnifiedManager()
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

      # Filter kwargs for solver based on required_args
      solver_info = selected_solver.get_solver_info()
      solver_kwargs = self._filter_kwargs(kwargs, solver_info.required_args)

      # Call solver to determine deployment
      params_result = selected_solver.solve_deployment(
        model_name=model_name,
        available_deployments=available_deployments,
        available_models=available_models,
        cache=self.cache,
        deployment_preference=deployment_preference,
        deployment_method=deployment_method,
        **solver_kwargs
      )

      if params_result.is_error():
        return params_result

      deployment_params = params_result.data
      logger.debug(f"Solver result: deployment={deployment_params.deployment_name} model={deployment_params.model_name} arch={deployment_params.architecture_name}")

      # Resolve model class from architecture plugins using architecture name
      model_class = self.manager.get_model_class(deployment_params.architecture_name)
      if not model_class:
        return Result.fail(f"No architecture '{deployment_params.architecture_name}' found for model '{deployment_params.model_name}'")

      # Resolve provider-specific model identifier for the selected architecture
      provider_model_name = deployment_params.model_name
      model_def = available_models.get(deployment_params.model_name)
      if model_def and getattr(model_def, 'identifiers', None):
        arch_key = deployment_params.architecture_name
        if arch_key in model_def.identifiers:
          provider_model_name = model_def.identifiers[arch_key]
          logger.debug(f"Resolved provider model name for arch '{arch_key}': {provider_model_name}")

      # Get deployment plugin
      selected_deployment = self.manager.get_deployment_plugin(deployment_params.deployment_name)
      if not selected_deployment:
        return Result.fail(f"Deployment method '{deployment_params.deployment_name}' not available")

      # Filter kwargs for deployment based on required_args
      deployment_info = selected_deployment.get_deployment_info()
      deployment_kwargs = self._filter_kwargs(kwargs, deployment_info.required_args)

      # Also get architecture kwargs for the model class
      available_architectures = self.manager.get_available_architectures()
      architecture_info = available_architectures.get(deployment_params.architecture_name)
      if architecture_info:
        architecture_kwargs = self._filter_kwargs(kwargs, architecture_info.required_args)
        # Merge architecture kwargs with deployment kwargs (deployment takes precedence)
        combined_kwargs = {**architecture_kwargs, **deployment_kwargs}
      else:
        combined_kwargs = deployment_kwargs

      # Let deployment plugin handle deployment + inference
      result = selected_deployment.run(
        model_name=provider_model_name,
        model_class=model_class,
        conversation=conversation,
        cache=self.cache,
        **combined_kwargs
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

  def _filter_kwargs(self, kwargs: Dict[str, Any], required_args: Optional[list]) -> Dict[str, Any]:
    """
    Filter kwargs to only include those specified in required_args.

    Args:
        kwargs: Dictionary of all available kwargs
        required_args: List of argument names that are required/allowed, or None if no args needed

    Returns:
        Filtered dictionary containing only the required arguments
    """
    if required_args is None or len(required_args) == 0:
      # If no required_args specified, return empty dict
      return {}

    # Filter to only include kwargs that are in the required_args list
    filtered = {}
    for arg_name in required_args:
      if arg_name in kwargs:
        filtered[arg_name] = kwargs[arg_name]

    return filtered
