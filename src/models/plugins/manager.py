"""
Plugin manager for the CLAIA models system.

This module provides the PluginManager class that handles plugin discovery,
registration, and coordination.
"""

import pluggy
import logging
from typing import Optional, Dict, List, Type, Any

# Internal dependencies
from ..base import BaseModel
from .hooks import ModelHooks, ModelInfo
from .base import ModelPlugin
from common.enums.model import ModelCapability


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                               CLASSES                                #
########################################################################
class PluginManager:
  """
  Manages model plugins and coordinates their interactions.

  This class handles plugin registration, discovery, and provides a unified
  interface for accessing plugin functionality.
  """

  def __init__(self):
    """Initialize the plugin manager."""
    self.pm = pluggy.PluginManager("claia_models")
    self.pm.add_hookspecs(ModelHooks)

    # Cache for supported models
    self._model_cache = None
    self._plugins_loaded = False

    logger.debug("PluginManager initialized")

  def register_plugin(self, plugin: ModelPlugin) -> None:
    """
    Register a plugin with the manager.

    Args:
        plugin: Plugin instance to register
    """
    self.pm.register(plugin)
    # Clear cache when new plugins are added
    self._model_cache = None
    logger.debug(f"Registered plugin: {plugin.plugin_name}")

  def load_builtin_plugins(self) -> None:
    """Load all built-in plugins."""
    if self._plugins_loaded:
      return

    # Import and register built-in plugins
    try:
      from .builtin.api_plugin import APIPlugin
      from .builtin.transformers_plugin import TransformersPlugin
      from .builtin.specialized_plugin import SpecializedPlugin

      self.register_plugin(APIPlugin())
      self.register_plugin(TransformersPlugin())
      self.register_plugin(SpecializedPlugin())

      self._plugins_loaded = True
      logger.info("Built-in plugins loaded successfully")

    except ImportError as e:
      logger.warning(f"Could not load some built-in plugins: {e}")

  def get_model_class(self, model_name: str, source: str, capability: Optional[ModelCapability] = None) -> Optional[Type[BaseModel]]:
    """
    Get the model class for a specific model and source.

    Args:
        model_name: Canonical model name
        source: Source/provider
        capability: Optional specific capability needed

    Returns:
        Model class if found, None otherwise
    """
    self.load_builtin_plugins()

    # Ask all plugins for the model class
    results = self.pm.hook.get_model_class(
      model_name=model_name,
      source=source,
      capability=capability
    )

    # Return first non-None result
    for result in results:
      if result is not None:
        logger.debug(f"Found model class for {model_name}/{source}")
        return result

    logger.debug(f"No model class found for {model_name}/{source}")
    return None

  def get_supported_models(self) -> Dict[str, ModelInfo]:
    """
    Get all models supported by registered plugins.

    Returns:
        Dict mapping model names to ModelInfo objects
    """
    if self._model_cache is not None:
      return self._model_cache

    self.load_builtin_plugins()

    # Collect models from all plugins
    all_models = {}
    results = self.pm.hook.get_supported_models()

    for plugin_models in results:
      if plugin_models:
        all_models.update(plugin_models)

    self._model_cache = all_models
    logger.debug(f"Collected {len(all_models)} supported models from plugins")
    return all_models

  def get_model_id(self, model_name: str, source: str) -> Optional[str]:
    """
    Get the actual model ID/path for a model and source.

    Args:
        model_name: Canonical model name
        source: Source/provider

    Returns:
        Model ID/path if found, None otherwise
    """
    self.load_builtin_plugins()

    results = self.pm.hook.get_model_id(
      model_name=model_name,
      source=source
    )

    # Return first non-None result
    for result in results:
      if result is not None:
        logger.debug(f"Found model ID for {model_name}/{source}: {result}")
        return result

    logger.debug(f"No model ID found for {model_name}/{source}")
    return None

  def supports_specialized_loading(self, model_name: str) -> bool:
    """
    Check if any plugin provides specialized loading for a model.

    Args:
        model_name: Model name to check

    Returns:
        True if specialized loading is available
    """
    self.load_builtin_plugins()

    results = self.pm.hook.supports_specialized_loading(model_name=model_name)

    # Return True if any plugin supports specialized loading
    return any(results)

  def resolve_model_name(self, model_name: str) -> str:
    """
    Resolve a model name or alias to its canonical name.

    Args:
        model_name: Model name or alias to resolve

    Returns:
        Canonical model name if found, original name otherwise
    """
    supported_models = self.get_supported_models()

    # Check if it's already a canonical name
    if model_name in supported_models:
      return model_name

    # Check aliases
    for canonical_name, model_info in supported_models.items():
      if model_info.aliases and model_name in model_info.aliases:
        logger.debug(f"Resolved alias '{model_name}' to '{canonical_name}'")
        return canonical_name

    # Return original if not found
    logger.debug(f"No resolution found for '{model_name}'")
    return model_name
