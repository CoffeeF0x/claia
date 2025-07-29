"""
Module manager for the CLAIA models system.

This module handles loading and coordinating all plugin types:
- Model plugins (implement specific AI models)
- Deployment plugins (handle deployment methods)
- Solver plugins (determine deployment strategies)
"""

import pluggy
import logging
import importlib.metadata as metadata
from typing import Optional, Dict, List, Type, Any

# Internal dependencies
from .hooks import ModelHooks, DeploymentHooks, SolverHooks
from .hooks import ModelInfo, DeploymentInfo, SolverInfo
from .base import BaseModel
from common.enums.model import ModelCapability



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                               CLASSES                                #
########################################################################
class ModuleManager:
  """
  Manages all plugin types for the CLAIA model system.

  This class coordinates three types of plugins:
  - Model plugins: Implement specific AI models
  - Deployment plugins: Handle deployment methods
  - Solver plugins: Determine deployment strategies
  """

  def __init__(self):
    """Initialize the module manager."""
    # Create separate plugin managers for each plugin type
    self.model_pm = pluggy.PluginManager("claia_models")
    self.model_pm.add_hookspecs(ModelHooks)

    self.deployment_pm = pluggy.PluginManager("claia_deployments")
    self.deployment_pm.add_hookspecs(DeploymentHooks)

    self.solver_pm = pluggy.PluginManager("claia_solvers")
    self.solver_pm.add_hookspecs(SolverHooks)

    # Caches
    self._model_cache = None
    self._plugins_loaded = False

    logger.debug("ModuleManager initialized")

  def load_all_plugins(self) -> None:
    """Load all plugins from entry points."""
    if self._plugins_loaded:
      return

    try:
      # Load plugins dynamically from entry points
      self._load_model_plugins()
      self._load_deployment_plugins()
      self._load_solver_plugins()

      self._plugins_loaded = True
      logger.info("All plugins loaded successfully")

    except Exception as e:
      logger.error(f"Error loading plugins: {e}")
      raise RuntimeError(f"Failed to load plugins: {e}")

  def _load_model_plugins(self) -> None:
    """Load model plugins from entry points."""
    loaded_count = 0

    try:
      # Load plugins from entry points
      for entry_point in metadata.entry_points().select(group='claia.models'):
        try:
          plugin_class = entry_point.load()
          plugin_instance = plugin_class()
          self.model_pm.register(plugin_instance)
          loaded_count += 1
          logger.debug(f"Loaded model plugin: {entry_point.name} from {entry_point.value}")
        except Exception as e:
          logger.warning(f"Failed to load model plugin {entry_point.name}: {e}")

      if loaded_count == 0:
        raise RuntimeError("No model plugins found in entry points")

      logger.info(f"Loaded {loaded_count} model plugins from entry points")

    except Exception as e:
      logger.error(f"Error loading model plugins from entry points: {e}")
      raise

  def _load_deployment_plugins(self) -> None:
    """Load deployment plugins from entry points."""
    loaded_count = 0

    try:
      # Load plugins from entry points
      for entry_point in metadata.entry_points().select(group='claia.deployments'):
        try:
          plugin_class = entry_point.load()
          plugin_instance = plugin_class()
          self.deployment_pm.register(plugin_instance)
          loaded_count += 1
          logger.debug(f"Loaded deployment plugin: {entry_point.name} from {entry_point.value}")
        except Exception as e:
          logger.warning(f"Failed to load deployment plugin {entry_point.name}: {e}")

      if loaded_count == 0:
        raise RuntimeError("No deployment plugins found in entry points")

      logger.info(f"Loaded {loaded_count} deployment plugins from entry points")

    except Exception as e:
      logger.error(f"Error loading deployment plugins from entry points: {e}")
      raise

  def _load_solver_plugins(self) -> None:
    """Load solver plugins from entry points."""
    loaded_count = 0

    try:
      # Load plugins from entry points
      for entry_point in metadata.entry_points().select(group='claia.solvers'):
        try:
          plugin_class = entry_point.load()
          plugin_instance = plugin_class()
          self.solver_pm.register(plugin_instance)
          loaded_count += 1
          logger.debug(f"Loaded solver plugin: {entry_point.name} from {entry_point.value}")
        except Exception as e:
          logger.warning(f"Failed to load solver plugin {entry_point.name}: {e}")

      if loaded_count == 0:
        raise RuntimeError("No solver plugins found in entry points")

      logger.info(f"Loaded {loaded_count} solver plugins from entry points")

    except Exception as e:
      logger.error(f"Error loading solver plugins from entry points: {e}")
      raise

  # Model plugin methods
  def get_model_class(self, model_name: str) -> Optional[Type[BaseModel]]:
    """Get the model class for a specific model."""
    self.load_all_plugins()

    results = self.model_pm.hook.get_model_class(model_name=model_name)

    for result in results:
      if result is not None:
        logger.debug(f"Found model class for {model_name}")
        return result

    logger.debug(f"No model class found for {model_name}")
    return None

  def get_supported_models(self) -> Dict[str, ModelInfo]:
    """Get all models supported by registered model plugins."""
    self.load_all_plugins()

    all_models = {}
    results = self.model_pm.hook.get_supported_models()

    for plugin_models in results:
      if plugin_models:
        all_models.update(plugin_models)

    logger.debug(f"Collected {len(all_models)} supported models")
    return all_models

  def get_model_id(self, model_name: str) -> Optional[str]:
    """Get the actual model ID/path for a model."""
    self.load_all_plugins()

    results = self.model_pm.hook.get_model_id(model_name=model_name)

    for result in results:
      if result is not None:
        logger.debug(f"Found model ID for {model_name}: {result}")
        return result

    return None

  # Deployment plugin methods
  def get_available_deployments(self) -> Dict[str, DeploymentInfo]:
    """Get all available deployment methods."""
    self.load_all_plugins()

    all_deployments = {}
    results = self.deployment_pm.hook.get_deployment_info()

    for deployment_info in results:
      if deployment_info:
        all_deployments[deployment_info.name] = deployment_info

    logger.debug(f"Collected {len(all_deployments)} deployment methods")
    return all_deployments

  def get_deployment_plugin(self, deployment_name: str):
    """Get a specific deployment plugin by name."""
    self.load_all_plugins()

    # Find the plugin that handles this deployment method
    for plugin in self.deployment_pm.get_plugins():
      info = plugin.get_deployment_info()
      if info.name == deployment_name:
        return plugin

    return None

  # Solver plugin methods
  def get_available_solvers(self) -> Dict[str, SolverInfo]:
    """Get all available deployment solvers."""
    self.load_all_plugins()

    all_solvers = {}
    results = self.solver_pm.hook.get_solver_info()

    for solver_info in results:
      if solver_info:
        all_solvers[solver_info.name] = solver_info

    logger.debug(f"Collected {len(all_solvers)} solvers")
    return all_solvers

  def get_solver_plugin(self, solver_name: str = None):
    """Get a specific solver plugin by name, or the best available solver."""
    self.load_all_plugins()

    if solver_name:
      # Find specific solver
      for plugin in self.solver_pm.get_plugins():
        info = plugin.get_solver_info()
        if info.name == solver_name:
          return plugin
    else:
      # Return highest priority solver
      best_plugin = None
      best_priority = float('inf')

      for plugin in self.solver_pm.get_plugins():
        info = plugin.get_solver_info()
        if info.priority < best_priority:
          best_priority = info.priority
          best_plugin = plugin

      return best_plugin

    return None

  def resolve_model_name(self, model_name: str) -> str:
    """Resolve a model name or alias to its canonical name."""
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
