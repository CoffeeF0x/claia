"""
Plugin-based ModelRegistry for the CLAIA application.

This module provides a refactored ModelRegistry that uses a plugin system
for extensibility and splits functionality into focused components.
"""

import logging
from typing import Any, Optional, Dict

# Internal dependencies
from common.results import Result
from common.files.conversation import Conversation
from common.enums.model import ModelCapability
from .config import ModelConfig
from .plugins import PluginManager
from .core import ModelResolver, ModelFactory, ModelCache, ModelExecutor


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                            MODEL REGISTRY                            #
########################################################################
class ModelRegistry:
  """
  Plugin-based ModelRegistry for managing models in the CLAIA application.

  This refactored registry uses a plugin system for extensibility and
  delegates functionality to specialized components:
  - PluginManager: Handles plugin discovery and coordination
  - ModelResolver: Name resolution and source selection
  - ModelFactory: Model instantiation
  - ModelCache: Model lifecycle management
  - ModelExecutor: Generation coordination
  """
  _instance = None

  def __new__(cls):
    """Create or return the singleton instance of ModelRegistry."""
    if cls._instance is None:
      logger.debug("Creating ModelRegistry singleton instance")
      cls._instance = super(ModelRegistry, cls).__new__(cls)
      cls._instance._initialized = False
    return cls._instance

  def __init__(self):
    """Initialize the ModelRegistry singleton."""
    if not self._initialized:
      logger.debug("Initializing Plugin-based Model Registry")

      # Initialize plugin system and core components
      self.plugin_manager = PluginManager()
      self.resolver = ModelResolver(self.plugin_manager)
      self.factory = ModelFactory(self.plugin_manager)
      self.cache = ModelCache()
      self.executor = ModelExecutor()

      # Initialize default config
      self._default_config = ModelConfig()

      self._initialized = True
      logger.info("Plugin-based ModelRegistry initialized successfully")

  def get_model(self, model_name: str, config: Optional[ModelConfig] = None, process_type: Optional[ModelCapability] = None, device: Optional[str] = None) -> Result:
    """
    Get the appropriate model based on the model name, source, and optional process type.

    Args:
      model_name: Name or alias of the model to get
      config: ModelConfig object containing configuration
      process_type: Optional capability filter
      device: Optional device specification

    Returns:
      Result containing the model instance or error data
    """
    try:
      logger.debug(f"Getting model: {model_name}")

      # Use default config if none provided
      if config is None:
        config = self._default_config

      # Resolve model name to canonical form
      canonical_model_name = self.resolver.resolve_model_name(model_name)
      if canonical_model_name != model_name:
        logger.debug(f"Resolved '{model_name}' to canonical name '{canonical_model_name}'")
        model_name = canonical_model_name

      # Check if we have a cached local model
      if self.cache.is_model_cached(model_name):
        cached_model = self.cache.get_cached_model(model_name)
        if cached_model:
          logger.debug(f"Using cached model for {model_name}")
          return Result(data=cached_model)

      # Find available sources
      available_sources = self.resolver.find_available_sources(model_name)
      if not available_sources:
        return Result.fail(f"No available sources found for model: {model_name}")

      # Select the best source
      active_model_source = getattr(config, 'active_model_source', None) if config else None
      chosen_source = self.resolver.select_source(model_name, available_sources, active_model_source)
      logger.debug(f"Selected source '{chosen_source}' for model '{model_name}'")

      # Get API key for the chosen source
      api_key = self.executor.get_api_key_for_source(chosen_source)

      # Create model instance
      model_result = self.factory.create_model(
        model_name=model_name,
        source=chosen_source,
        device=device,
        config=config
      )

      if model_result.is_error():
        return model_result

      model = model_result.data

      # Cache local models
      if hasattr(model, 'model_path'):  # Local model
        self.cache.cache_model(model_name, model)

      logger.debug(f"Successfully created model instance for {model_name}")
      return Result(data=model)

    except Exception as e:
      logger.error(f"Error getting model {model_name}: {str(e)}")
      return Result.fail(f"Failed to get model: {str(e)}")

  def run(self, model_name: str, conversation: Conversation, process_type: Optional[ModelCapability] = None, device: Optional[str] = None, config: Optional[ModelConfig] = None, **kwargs) -> Result:
    """
    Run the model with the given conversation.

    Args:
      model_name: Name or alias of the model
      conversation: Conversation to process
      process_type: Optional capability filter
      device: Optional device specification
      config: Optional model configuration
      **kwargs: Additional generation parameters

    Returns:
      Result containing the generated response
    """
    logger.debug(f"Running model {model_name} with {conversation.metadata.get('message_count', 0)} messages")

    # Get model instance
    model_result = self.get_model(
      model_name=model_name,
      config=config,
      process_type=process_type,
      device=device
    )

    if model_result.is_error():
      logger.error(f"Failed to get model {model_name}: {model_result.message}")
      return model_result

    model = model_result.data

    # Execute generation
    return self.executor.execute(
      model=model,
      conversation=conversation,
      config=config,
      **kwargs
    )

  def get_supported_models(self) -> Dict[str, Any]:
    """
    Get all models supported by registered plugins.

    Returns:
        Dict mapping model names to model information
    """
    return self.plugin_manager.get_supported_models()

  def get_loaded_models(self) -> Dict[str, Any]:
    """Get dictionary of currently loaded local models."""
    return self.cache.get_loaded_models()

  def unload_model(self, model_name: str) -> Result:
    """Unload a model from memory."""
    return self.cache.unload_model(model_name)

  def unload_all_models(self) -> Result:
    """Unload all loaded models from memory."""
    return self.cache.unload_all_models()

  def get_cache_stats(self) -> Dict[str, Any]:
    """Get statistics about the model cache."""
    return self.cache.get_cache_stats()

  def register_plugin(self, plugin) -> None:
    """
    Register a custom plugin with the registry.

    Args:
        plugin: Plugin instance to register
    """
    self.plugin_manager.register_plugin(plugin)
    logger.info(f"Registered custom plugin: {plugin.plugin_name}")

  # Backwards compatibility methods
  def get_best_available_device(self) -> str:
    """Get the best available device for model execution."""
    return self.factory.get_best_available_device()

  def resolve_model_name(self, model_name: str) -> str:
    """Resolve a model name or alias to its canonical name."""
    return self.resolver.resolve_model_name(model_name)

  def find_available_sources(self, model_name: str):
    """Find available sources for a given model name."""
    return self.resolver.find_available_sources(model_name)
