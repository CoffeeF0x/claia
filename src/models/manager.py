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
from .hooks import ArchitectureHooks, DeploymentHooks, SolverHooks, DefinitionHooks
from .hooks import ArchitectureInfo, DeploymentInfo, SolverInfo, ModelDefinition
from .base import BaseModel
from common.enums.model import ModelCapability



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                              CONSTANTS                               #
########################################################################
DEFAULT_SOLVER = "default"



########################################################################
#                               CLASSES                                #
########################################################################
class ModuleManager:
  """
  Manages all plugin types for the CLAIA model system.

  This class coordinates four types of plugins:
  - Architecture plugins: Implement specific AI model architectures
  - Deployment plugins: Handle deployment methods
  - Solver plugins: Determine deployment strategies
  - Definition plugins: Provide model metadata
  """

  def __init__(self):
    """Initialize the module manager."""
    # Create separate plugin managers for each plugin type
    self.architecture_pm = pluggy.PluginManager("claia_architectures")
    self.architecture_pm.add_hookspecs(ArchitectureHooks)

    self.deployment_pm = pluggy.PluginManager("claia_deployments")
    self.deployment_pm.add_hookspecs(DeploymentHooks)

    self.solver_pm = pluggy.PluginManager("claia_solvers")
    self.solver_pm.add_hookspecs(SolverHooks)

    self.definition_pm = pluggy.PluginManager("claia_definitions")
    self.definition_pm.add_hookspecs(DefinitionHooks)

    self._plugins_loaded = False

    logger.debug("ModuleManager initialized")

  def load_all_plugins(self) -> None:
    """Load all plugins from entry points."""
    if self._plugins_loaded:
      return

    try:
      # Load plugins dynamically from entry points
      self._load_architecture_plugins()
      self._load_deployment_plugins()
      self._load_solver_plugins()
      self._load_definition_plugins()

      self._plugins_loaded = True
      logger.info("All plugins loaded successfully")

    except Exception as e:
      logger.error(f"Error loading plugins: {e}")
      raise RuntimeError(f"Failed to load plugins: {e}")

  def _load_architecture_plugins(self) -> None:
    """Load architecture plugins from entry points."""
    loaded_count = 0

    try:
      # Load plugins from entry points
      for entry_point in metadata.entry_points().select(group='claia.architectures'):
        try:
          plugin_class = entry_point.load()
          plugin_instance = plugin_class()
          self.architecture_pm.register(plugin_instance)
          loaded_count += 1
          logger.debug(f"Loaded architecture plugin: {entry_point.name} from {entry_point.value}")
        except Exception as e:
          logger.warning(f"Failed to load architecture plugin {entry_point.name}: {e}")

      if loaded_count == 0:
        raise RuntimeError("No architecture plugins found in entry points")

      logger.info(f"Loaded {loaded_count} architecture plugins from entry points")

    except Exception as e:
      logger.error(f"Error loading architecture plugins from entry points: {e}")
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

  def _load_definition_plugins(self) -> None:
    """Load definition plugins from entry points."""
    loaded_count = 0

    try:
      # Load plugins from entry points
      for entry_point in metadata.entry_points().select(group='claia.definitions'):
        try:
          plugin_class = entry_point.load()
          plugin_instance = plugin_class()
          self.definition_pm.register(plugin_instance)
          loaded_count += 1
          logger.debug(f"Loaded definition plugin: {entry_point.name} from {entry_point.value}")
        except Exception as e:
          logger.warning(f"Failed to load definition plugin {entry_point.name}: {e}")

      if loaded_count == 0:
        logger.warning("No definition plugins found in entry points")
      else:
        logger.info(f"Loaded {loaded_count} definition plugins from entry points")

    except Exception as e:
      logger.error(f"Error loading definition plugins from entry points: {e}")
      # Don't raise for definition plugins - they're optional
      logger.warning("Continuing without definition plugins")

  # Architecture plugin methods
  def get_model_class(self, model_name: str) -> Optional[Type[BaseModel]]:
    """Get the model class for a specific model from architecture plugins."""
    self.load_all_plugins()

    results = self.architecture_pm.hook.get_model_class(model_name=model_name)

    for result in results:
      if result is not None:
        logger.debug(f"Found model class for {model_name}")
        return result

    logger.debug(f"No model class found for {model_name}")
    return None

  def get_supported_models(self) -> Dict[str, ModelDefinition]:
    """Get all model definitions from registered definition plugins."""
    self.load_all_plugins()

    all_definitions = {}
    results = self.definition_pm.hook.get_model_definitions()

    for plugin_definitions in results:
      if plugin_definitions:
        # Merge definitions, allowing later plugins to extend/override
        for name, definition in plugin_definitions.items():
          if name in all_definitions:
            # Merge fields, keeping non-None values from the new definition
            existing = all_definitions[name]
            merged = ModelDefinition(
              name=name,
              title=definition.title or existing.title,
              aliases=self._merge_lists(existing.aliases, definition.aliases),
              company=definition.company or existing.company,
              deployments=self._merge_lists(existing.deployments, definition.deployments),
              architectures=self._merge_lists(existing.architectures, definition.architectures),
              description=definition.description or existing.description,
              parameters=definition.parameters or existing.parameters,
              context_length=definition.context_length or existing.context_length,
              capabilities=self._merge_lists(existing.capabilities, definition.capabilities),
              license=definition.license or existing.license,
              url=definition.url or existing.url
            )
            all_definitions[name] = merged
          else:
            all_definitions[name] = definition

    logger.debug(f"Collected {len(all_definitions)} model definitions")
    return all_definitions

  def _merge_lists(self, list1: Optional[List[str]], list2: Optional[List[str]]) -> Optional[List[str]]:
    """Merge two optional lists, removing duplicates."""
    if not list1 and not list2:
      return None

    result = []
    if list1:
      result.extend(list1)
    if list2:
      for item in list2:
        if item not in result:
          result.append(item)

    return result if result else None

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
    """Get a specific solver plugin by name, or the default solver."""
    self.load_all_plugins()

    # Use default solver if none specified
    if not solver_name:
      solver_name = DEFAULT_SOLVER

    # Find the requested solver
    for plugin in self.solver_pm.get_plugins():
      info = plugin.get_solver_info()
      if info.name == solver_name:
        return plugin

    # Return None if not found
    logger.warning(f"Solver '{solver_name}' not found")
    return None
