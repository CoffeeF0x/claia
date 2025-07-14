"""
Model caching and lifecycle management.

This module handles caching of loaded models and managing their lifecycle
to optimize memory usage and loading times.
"""

import logging
from typing import Dict, Any

# Internal dependencies
from common.results import Result


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                               CLASSES                                #
########################################################################
class ModelCache:
  """
  Handles model caching and lifecycle management.

  This component is responsible for:
  - Caching loaded local models to avoid repeated loading
  - Managing model lifecycle (loading, unloading)
  - Memory optimization through selective model management
  """

  def __init__(self):
    """Initialize the model cache."""
    # Store loaded local models with model_name as key
    self._loaded_local_models = {}
    logger.debug("ModelCache initialized")

  def get_cached_model(self, model_name: str) -> Any:
    """
    Get a cached model if available.

    Args:
        model_name: Name of the model to retrieve

    Returns:
        Cached model instance or None if not cached
    """
    cached_model = self._loaded_local_models.get(model_name)
    if cached_model:
      logger.debug(f"Retrieved cached model: {model_name}")
    else:
      logger.debug(f"No cached model found for: {model_name}")
    return cached_model

  def cache_model(self, model_name: str, model: Any) -> None:
    """
    Cache a model instance.

    Args:
        model_name: Name of the model
        model: Model instance to cache
    """
    self._loaded_local_models[model_name] = model
    logger.debug(f"Cached model: {model_name}")

  def is_model_cached(self, model_name: str) -> bool:
    """
    Check if a model is cached.

    Args:
        model_name: Name of the model to check

    Returns:
        True if model is cached, False otherwise
    """
    return model_name in self._loaded_local_models

  def get_loaded_models(self) -> Dict[str, Any]:
    """
    Get dictionary of currently loaded local models.

    Returns:
        Dict mapping model names to model instances
    """
    return self._loaded_local_models.copy()

  def unload_model(self, model_name: str) -> Result:
    """
    Unload a model from memory.

    Args:
        model_name: Name of the model to unload

    Returns:
        Result object indicating success or failure
    """
    if model_name in self._loaded_local_models:
      try:
        model = self._loaded_local_models[model_name]

        # Call unload method if available
        if hasattr(model, 'unload'):
          model.unload()

        # Remove from cache
        del self._loaded_local_models[model_name]
        logger.info(f"Successfully unloaded model: {model_name}")
        return Result()

      except Exception as e:
        logger.error(f"Error unloading model {model_name}: {str(e)}")
        return Result.fail(f"Error unloading model: {str(e)}")
    else:
      return Result.fail(f"Model {model_name} is not loaded")

  def unload_all_models(self) -> Result:
    """
    Unload all loaded models from memory.

    Returns:
        Result object indicating success or failure
    """
    errors = []

    # Create a list of model names to avoid modification during iteration
    model_names = list(self._loaded_local_models.keys())

    for model_name in model_names:
      result = self.unload_model(model_name)
      if result.is_error():
        errors.append(f"{model_name}: {result.message}")

    if errors:
      error_message = f"Errors unloading models: {', '.join(errors)}"
      logger.error(error_message)
      return Result.fail(error_message)
    else:
      logger.info("Successfully unloaded all models")
      return Result()

  def get_cache_stats(self) -> Dict[str, Any]:
    """
    Get statistics about the model cache.

    Returns:
        Dict containing cache statistics
    """
    stats = {
      "loaded_models_count": len(self._loaded_local_models),
      "loaded_models": list(self._loaded_local_models.keys())
    }

    # Add memory usage information if possible
    try:
      import psutil
      process = psutil.Process()
      stats["memory_usage_mb"] = process.memory_info().rss / 1024 / 1024
    except ImportError:
      logger.debug("psutil not available for memory statistics")

    return stats

  def clear_cache(self) -> Result:
    """
    Clear the entire model cache.

    This is equivalent to unloading all models.

    Returns:
        Result object indicating success or failure
    """
    return self.unload_all_models()
