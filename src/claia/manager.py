"""
Unified manager for the CLAIA system.

This module handles loading and coordinating all plugin types:
- Model architectures (implement specific AI models)
- Model deployments (handle deployment methods)
- Model solvers (determine deployment strategies)
- Model definitions (provide model metadata)
- Tool patterns (define how tools are used)
- Tool protocols (handle tool execution)
- Tool modules (provide tool implementations)
"""

import pluggy
import logging
import importlib.metadata as metadata
from typing import Dict, Optional, List, Type

from .hooks import (
  ArchitectureHooks, DeploymentHooks, SolverHooks, DefinitionHooks,
  PatternHooks, ProtocolHooks, CommandModuleHooks, AgentHooks,
  DeploymentInfo, SolverInfo, ModelDefinition, ArchitectureInfo, AgentInfo
)
from claia.lib.model.base import BaseModel
from .lib import BaseAgent


logger = logging.getLogger(__name__)


# Constants
DEFAULT_SOLVER = "default"


class UnifiedManager:
  """
  Unified manager for all CLAIA plugin types.

  This class coordinates all plugin types for models, tools, and agents:
  - Model: Architecture, Deployment, Solver, Definition plugins
  - Tools: Pattern, Protocol, CommandModule plugins
  - Agents: Agent plugins
  """

  def __init__(self):
    """Initialize the unified manager."""
    # Model plugin managers
    self.architecture_pm = pluggy.PluginManager("claia_architectures")
    self.architecture_pm.add_hookspecs(ArchitectureHooks)

    self.deployment_pm = pluggy.PluginManager("claia_deployments")
    self.deployment_pm.add_hookspecs(DeploymentHooks)

    self.solver_pm = pluggy.PluginManager("claia_solvers")
    self.solver_pm.add_hookspecs(SolverHooks)

    self.definition_pm = pluggy.PluginManager("claia_definitions")
    self.definition_pm.add_hookspecs(DefinitionHooks)

    # Tool plugin managers
    self.pattern_pm = pluggy.PluginManager("claia_tool_patterns")
    self.pattern_pm.add_hookspecs(PatternHooks)

    self.protocol_pm = pluggy.PluginManager("claia_tool_protocols")
    self.protocol_pm.add_hookspecs(ProtocolHooks)

    self.module_pm = pluggy.PluginManager("claia_command_modules")
    self.module_pm.add_hookspecs(CommandModuleHooks)

    # Agent plugin manager
    self.agent_pm = pluggy.PluginManager("claia_agents")
    self.agent_pm.add_hookspecs(AgentHooks)

    self._plugins_loaded = False
    logger.debug("UnifiedManager initialized")

  def load_all_plugins(self, **kwargs) -> None:
    """Load all plugins from entry points."""
    if self._plugins_loaded:
      logger.debug("Plugins already loaded")
      return

    try:
      # Load definition plugins first (they're optional)
      self._load_definition_plugins()

      # Load tool plugins (pass in kwargs to process required_args)
      self._load_tool_plugins(**kwargs)

      # Load agent plugins
      self._load_agent_plugins()

      # Load model plugins
      self._load_architecture_plugins()
      self._load_deployment_plugins()
      self._load_solver_plugins()

      self._plugins_loaded = True
      logger.info("All plugins loaded successfully")

    except Exception as e:
      logger.error(f"Error loading plugins: {e}")
      raise RuntimeError(f"Failed to load plugins: {e}")

  # Model plugin loading methods
  def _load_architecture_plugins(self) -> None:
    """Load architecture plugins from entry points."""
    loaded_count = 0

    try:
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

  # Tool plugin loading method
  def _load_tool_plugins(self, **kwargs) -> None:
    """Load all tool plugins."""
    self._load_group('claia.tool_patterns', self.pattern_pm, 'pattern', **kwargs)
    self._load_group('claia.tool_protocols', self.protocol_pm, 'protocol', **kwargs)
    self._load_group('claia.command_modules', self.module_pm, 'module', **kwargs)

  def _load_group(self, group: str, pm: pluggy.PluginManager, label: str, **kwargs) -> None:
    """Load a group of tool plugins with fallbacks."""
    loaded = 0
    for ep in metadata.entry_points().select(group=group):
      try:
        cls = ep.load()

        # For command modules, pass required_args during initialization
        if group == 'claia.command_modules':
          inst = self._create_module_instance(cls, **kwargs)
        else:
          inst = cls()

        pm.register(inst)
        loaded += 1
        logger.debug(f"Loaded {label} plugin: {ep.name} from {ep.value}")
      except Exception as e:
        logger.warning(f"Failed to load {label} plugin {ep.name}: {e}")

  def _create_module_instance(self, cls, **kwargs):
    """Create a module instance with required_args passed to constructor."""
    try:
      # Create a temporary instance to get module info
      temp_inst = cls()
      module_info = temp_inst.get_module_info()

      # Get required_args if specified
      required_args = getattr(module_info, 'required_args', None)
      if required_args and kwargs:
        filtered_kwargs = self._filter_kwargs(kwargs, required_args)
        return cls(**filtered_kwargs)
      else:
        return temp_inst
    except Exception as e:
      logger.warning(f"Error creating module instance with required_args, falling back to no-args constructor: {e}")
      return cls()

  def _filter_kwargs(self, kwargs, required_args):
    """Filter kwargs to only include those specified in required_args."""
    if required_args is None or len(required_args) == 0:
      return {}

    filtered = {}
    for arg_name in required_args:
      if arg_name in kwargs:
        filtered[arg_name] = kwargs[arg_name]
    return filtered

  # Model-specific methods
  def get_available_architectures(self) -> Dict[str, ArchitectureInfo]:
    """Get all available architecture plugins and their info keyed by name."""
    self.load_all_plugins()
    all_arch = {}
    infos = self.architecture_pm.hook.get_architecture_info()
    for info in infos:
      if info:
        all_arch[info.name] = info
    logger.debug(f"Collected {len(all_arch)} architectures")
    return all_arch

  def get_model_class(self, architecture_name: str) -> Optional[Type[BaseModel]]:
    """Get the model class for a specific architecture by name."""
    self.load_all_plugins()
    for plugin in self.architecture_pm.get_plugins():
      try:
        info = plugin.get_architecture_info()
        if info and info.name == architecture_name:
          model_class = plugin.get_model_class()
          if model_class:
            logger.debug(f"Found model class for architecture {architecture_name}")
            return model_class
      except Exception as e:
        logger.warning(f"Failed retrieving model class for architecture {architecture_name}: {e}")

    logger.debug(f"No model class found for architecture {architecture_name}")
    return None

  def get_supported_models(self) -> Dict[str, ModelDefinition]:
    """Get all model definitions from registered definition plugins."""
    self.load_all_plugins()
    all_definitions = {}
    results = self.definition_pm.hook.get_model_definitions()

    for plugin_definitions in results:
      if plugin_definitions:
        for name, definition in plugin_definitions.items():
          if name in all_definitions:
            # Merge definitions, allowing later plugins to extend/override
            existing = all_definitions[name]
            merged = ModelDefinition(
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
              url=definition.url or existing.url,
              identifiers=self._merge_dicts(existing.identifiers, definition.identifiers)
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

  def _merge_dicts(self, dict1: Optional[Dict[str, str]], dict2: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
    """Merge two optional dicts with last-wins on key conflicts."""
    if not dict1 and not dict2:
      return None
    merged: Dict[str, str] = {}
    if dict1:
      merged.update(dict1)
    if dict2:
      merged.update(dict2)  # dict2 overrides dict1 on conflicts
    return merged if merged else None

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
    for plugin in self.deployment_pm.get_plugins():
      info = plugin.get_deployment_info()
      if info.name == deployment_name:
        return plugin
    return None

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
    if not solver_name:
      solver_name = DEFAULT_SOLVER
    for plugin in self.solver_pm.get_plugins():
      info = plugin.get_solver_info()
      if info.name == solver_name:
        return plugin
    logger.warning(f"Solver '{solver_name}' not found")
    return None

  # Tool-specific methods
  def get_protocol_by_name(self, name: str):
    """Get a tool protocol plugin by name."""
    self.load_all_plugins()
    for plugin in self.protocol_pm.get_plugins():
      info = plugin.get_protocol_info()
      if info and info.name == name:
        return plugin, info
    return None, None

  def get_module_by_name(self, name: str):
    """Get a tool module plugin by name."""
    self.load_all_plugins()
    for plugin in self.module_pm.get_plugins():
      info = plugin.get_module_info()
      if info and info.name == name:
        return plugin, info
    return None, None

  def get_command_by_name(self, command_name: str):
    """Find a command by name across all loaded modules."""
    self.load_all_plugins()

    if '.' in command_name:
      module_name, cmd_name = command_name.split('.', 1)
      for plugin in self.module_pm.get_plugins():
        info = plugin.get_module_info()
        if info and info.name == module_name and hasattr(plugin, 'get_module_commands'):
          commands = plugin.get_module_commands()
          if cmd_name in commands:
            return plugin, commands[cmd_name], info
      return None, None, None

    for plugin in self.module_pm.get_plugins():
      info = plugin.get_module_info()
      if info and hasattr(plugin, 'get_module_commands'):
        commands = plugin.get_module_commands()
        if command_name in commands:
          return plugin, commands[command_name], info
    return None, None, None

  def get_all_commands(self) -> Dict[str, Dict]:
    """Get all available commands in hierarchical format."""
    self.load_all_plugins()
    result = {}

    for plugin in self.module_pm.get_plugins():
      info = plugin.get_module_info()
      if not info or not hasattr(plugin, 'get_module_commands'):
        continue

      module_entry = {
        "module_info": info,
        "list_of_commands": []
      }

      commands = plugin.get_module_commands()
      for cmd_name, cmd_def in commands.items():
        arguments_info = []
        if cmd_def.arguments:
          for arg_name, arg_def in cmd_def.arguments.items():
            arguments_info.append({
              "name": arg_name,
              "description": arg_def.description,
              "data_type": arg_def.data_type,
              "required": arg_def.required,
              "default_value": getattr(arg_def, 'default_value', None)
            })

        module_entry["list_of_commands"].append({
          "command_name": cmd_name,
          "command_description": cmd_def.description,
          "command_callable": cmd_def.callable,
          "arguments": arguments_info
        })

      result[info.name] = module_entry
    return result

  def get_pattern_by_name(self, name: str):
    """Get a tool pattern plugin by name."""
    self.load_all_plugins()
    for plugin in self.pattern_pm.get_plugins():
      info = plugin.get_pattern_info()
      if info and info.name == name:
        return plugin, info
    return None, None

  def get_default_pattern(self):
    """Get the default pattern plugin."""
    self.load_all_plugins()
    patterns = list(self.pattern_pm.get_plugins())
    return patterns[0] if patterns else None

  # Agent plugin loading and methods
  def _load_agent_plugins(self) -> None:
    """Load agent plugins from entry points."""
    loaded_count = 0

    try:
      for entry_point in metadata.entry_points().select(group='claia.agents'):
        try:
          plugin_class = entry_point.load()
          plugin_instance = plugin_class()
          self.agent_pm.register(plugin_instance)
          loaded_count += 1
          logger.debug(f"Loaded agent plugin: {entry_point.name} from {entry_point.value}")
        except Exception as e:
          logger.warning(f"Failed to load agent plugin {entry_point.name}: {e}")

      if loaded_count == 0:
        logger.warning("No agent plugins found in entry points, using built-in agents")

      logger.info(f"Loaded {loaded_count} agent plugins from entry points")

    except Exception as e:
      logger.error(f"Error loading agent plugins from entry points: {e}")
      raise

  def get_agent_class(self, agent_name: str) -> Optional[Type[BaseAgent]]:
    """Get the agent class for a specific agent name."""
    self.load_all_plugins()

    results = self.agent_pm.hook.get_agent_class(agent_name=agent_name)
    for result in results:
      if result is not None:
        logger.debug(f"Found agent class {result.__name__} for {agent_name}")
        return result

    logger.debug(f"No agent class found for {agent_name}")
    return None
