"""
Manager for the CLAIA system.

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
from typing import Dict, Optional, List, Type, Any, Callable, Tuple

from .hooks import (
  ArchitectureHooks, DeploymentHooks, SolverHooks, DefinitionHooks,
  PatternHooks, ProtocolHooks, ToolModuleHooks, AgentHooks,
  DeploymentInfo, SolverInfo, ModelDefinition, ArchitectureInfo, AgentInfo
)
from claia.lib.model.base import BaseModel
from .lib import BaseAgent



########################################################################
#                              CONSTANTS                               #
########################################################################
DEFAULT_SOLVER = "default"

# Map entry point group -> plugin info method name
INFO_METHOD_BY_GROUP: Dict[str, Optional[str]] = {
  'claia.architectures': 'get_architecture_info',
  'claia.deployments': 'get_deployment_info',
  'claia.solvers': 'get_solver_info',
  'claia.definitions': None,          # definitions expose definitions via hook, not a single info
  'claia.tool_patterns': 'get_pattern_info',
  'claia.tool_protocols': 'get_protocol_info',
  'claia.tool_modules': 'get_module_info',
  'claia.agents': 'get_agent_info',   # best-effort; if missing, we won't pass kwargs
}



########################################################################
#                              INITIALIZE                              #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                               MANAGER                                #
########################################################################
class Manager:
  """
  Manager for all CLAIA plugin types.

  This class coordinates all plugin types for models, tools, and agents:
  - Model: Architecture, Deployment, Solver, Definition plugins
  - Tools: Pattern, Protocol, CommandModule plugins
  - Agents: Agent plugins
  """

  def __init__(self):
    """Initialize the manager."""
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

    self.module_pm = pluggy.PluginManager("claia_tool_modules")
    self.module_pm.add_hookspecs(ToolModuleHooks)

    # Agent plugin manager
    self.agent_pm = pluggy.PluginManager("claia_agents")
    self.agent_pm.add_hookspecs(AgentHooks)

    # Programmatically registered agents
    self._registered_agents: Dict[str, AgentInfo] = {}

    self._plugins_loaded = False
    logger.debug("Manager initialized")

  def load_all_plugins(self, **kwargs) -> None:
    """Load all plugins from entry points."""
    if self._plugins_loaded:
      logger.debug("Plugins already loaded")
      return

    try:
      # Load definition plugins first (they're optional)
      self._load_plugins(group='claia.definitions', pm=self.definition_pm, label='definition', allow_empty=True, ctor_kwargs=kwargs)

      # Load tool plugins (pass in kwargs to process required_args)
      self._load_plugins(group='claia.tool_patterns', pm=self.pattern_pm, label='pattern', allow_empty=True, ctor_kwargs=kwargs)
      self._load_plugins(group='claia.tool_protocols', pm=self.protocol_pm, label='protocol', allow_empty=True, ctor_kwargs=kwargs)
      self._load_plugins(group='claia.tool_modules', pm=self.module_pm, label='module', allow_empty=True, ctor_kwargs=kwargs)

      # Load agent plugins (optional)
      self._load_plugins(group='claia.agents', pm=self.agent_pm, label='agent', allow_empty=True, ctor_kwargs=kwargs)

      # Load model plugins (required)
      self._load_plugins(group='claia.architectures', pm=self.architecture_pm, label='architecture', allow_empty=False, ctor_kwargs=kwargs)
      self._load_plugins(group='claia.deployments', pm=self.deployment_pm, label='deployment', allow_empty=False, ctor_kwargs=kwargs)
      self._load_plugins(group='claia.solvers', pm=self.solver_pm, label='solver', allow_empty=False, ctor_kwargs=kwargs)

      self._plugins_loaded = True
      logger.info("All plugins loaded")

    except Exception as e:
      logger.error(f"Error loading plugins: {e}")
      raise RuntimeError(f"Failed to load plugins: {e}")


  ######################################################################
  #                               UTILS                                #
  ######################################################################
  # Generic plugin loading helper
  def _load_plugins(self, group: str, pm: pluggy.PluginManager, label: str, allow_empty: bool = False, ctor_kwargs: Optional[Dict[str, Any]] = None) -> None:
    """Load plugins securely by filtering ctor kwargs based on required_args.

    We instantiate each plugin twice at most:
      1) Create a temporary no-arg instance to introspect its info and required_args
      2) If required_args is present, re-instantiate with only filtered kwargs
         Otherwise, register the temporary instance
    """
    loaded_count = 0
    try:
      for ep in metadata.entry_points().select(group=group):
        try:
          cls = ep.load()
          inst = None

          # Step 1: always try to build a temporary instance without kwargs
          try:
            temp = cls()
          except Exception as e:
            logger.warning(f"Failed to instantiate {label} plugin {ep.name} without kwargs: {e}")
            # As a last resort, do not pass full ctor_kwargs (security); skip this plugin
            continue

          # Step 2: if the plugin exposes an info method with required_args, filter
          info_method = self._get_info_method_for_group(group)
          filtered_kwargs: Dict[str, Any] = {}
          if info_method and hasattr(temp, info_method):
            try:
              info_obj = getattr(temp, info_method)()
              req = getattr(info_obj, 'required_args', None)
              if req and ctor_kwargs:
                filtered_kwargs = self._filter_kwargs(ctor_kwargs, req)
            except Exception as e:
              logger.debug(f"Could not inspect required_args for {label} plugin {ep.name}: {e}")

          # If we have any filtered kwargs to pass, re-instantiate with them
          if filtered_kwargs:
            try:
              inst = cls(**filtered_kwargs)
            except Exception as e:
              logger.debug(f"Re-instantiating {label} plugin {ep.name} with filtered kwargs failed, using temp instance: {e}")
              inst = temp
          else:
            # No required args or none provided — register temp instance (no secrets)
            inst = temp

          pm.register(inst)
          loaded_count += 1
          logger.debug(f"Loaded {label} plugin: {ep.name} from {ep.value}")
        except Exception as e:
          logger.warning(f"Failed to load {label} plugin {ep.name}: {e}")

      if loaded_count == 0:
        msg = f"No {label} plugins found in entry points"
        if allow_empty:
          logger.warning(msg)
        else:
          raise RuntimeError(msg)

      logger.info(f"Loaded {loaded_count} {label} plugin(s) from entry points")
    except Exception as e:
      logger.error(f"Error loading {label} plugins from entry points: {e}")
      if not allow_empty:
        raise

  def _get_info_method_for_group(self, group: str) -> Optional[str]:
    """Return the instance info method name for a given entry point group."""
    return INFO_METHOD_BY_GROUP.get(group)

  def _filter_kwargs(self, kwargs, required_args):
    """Filter kwargs to only include those specified in required_args."""
    if required_args is None or len(required_args) == 0:
      return {}

    filtered = {}
    for arg_name in required_args:
      if arg_name in kwargs:
        filtered[arg_name] = kwargs[arg_name]
    return filtered

  # Generic helpers for lookups and info collection
  def _find_plugin_by_name(self, pm: pluggy.PluginManager, info_method: str, name: str) -> Tuple[Optional[Any], Optional[Any]]:
    """Find a registered plugin by its info.name using the given info_method.

    Returns (plugin, info) tuple; (None, None) if not found.
    """
    for plugin in pm.get_plugins():
      try:
        info = getattr(plugin, info_method)()
        if info and getattr(info, 'name', None) == name:
          return plugin, info
      except Exception as e:
        logger.warning(f"Failed retrieving {info_method} for plugin {plugin}: {e}")
    return None, None

  def _collect_info_dict(self, pm: pluggy.PluginManager, hook_name: str) -> Dict[str, Any]:
    """Collect hook-returned info objects into a dict keyed by info.name."""
    all_items: Dict[str, Any] = {}
    try:
      hook = getattr(pm.hook, hook_name)
      results = hook()
      for info in results:
        if info:
          name = getattr(info, 'name', None)
          if name:
            all_items[name] = info
    except Exception as e:
      logger.warning(f"Failed collecting items via hook {hook_name}: {e}")
    return all_items

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


  ######################################################################
  #                              GETTERS                               #
  ######################################################################
  # MODELS
  def get_available_architectures(self) -> Dict[str, ArchitectureInfo]:
    """Get all available architecture plugins and their info keyed by name."""
    self.load_all_plugins()
    all_arch = self._collect_info_dict(self.architecture_pm, 'get_architecture_info')
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
    results = self.definition_pm.hook.get_definitions()

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

  def get_available_deployments(self) -> Dict[str, DeploymentInfo]:
    """Get all available deployment methods."""
    self.load_all_plugins()
    all_deployments = self._collect_info_dict(self.deployment_pm, 'get_deployment_info')
    logger.debug(f"Collected {len(all_deployments)} deployment methods")
    return all_deployments

  def get_deployment_plugin(self, deployment_name: str):
    """Get a specific deployment plugin by name."""
    self.load_all_plugins()
    plugin, _ = self._find_plugin_by_name(self.deployment_pm, 'get_deployment_info', deployment_name)
    return plugin

  def get_available_solvers(self) -> Dict[str, SolverInfo]:
    """Get all available deployment solvers."""
    self.load_all_plugins()
    all_solvers = self._collect_info_dict(self.solver_pm, 'get_solver_info')
    logger.debug(f"Collected {len(all_solvers)} solvers")
    return all_solvers

  def get_solver_plugin(self, solver_name: str = None):
    """Get a specific solver plugin by name, or the default solver."""
    self.load_all_plugins()
    if not solver_name:
      solver_name = DEFAULT_SOLVER
    plugin, _ = self._find_plugin_by_name(self.solver_pm, 'get_solver_info', solver_name)
    if plugin:
      return plugin
    logger.warning(f"Solver '{solver_name}' not found")
    return None


  # TOOLS
  def get_protocol_by_name(self, name: str):
    """Get a tool protocol plugin by name."""
    self.load_all_plugins()
    return self._find_plugin_by_name(self.protocol_pm, 'get_protocol_info', name)

  def get_module_by_name(self, name: str):
    """Get a tool module plugin by name."""
    self.load_all_plugins()
    return self._find_plugin_by_name(self.module_pm, 'get_module_info', name)

  def get_tool_by_name(self, command_name: str):
    """Find a tool by name across all loaded modules."""
    self.load_all_plugins()

    if '.' in command_name:
      module_name, cmd_name = command_name.split('.', 1)
      for plugin in self.module_pm.get_plugins():
        info = plugin.get_module_info()
        if info and info.name == module_name and hasattr(plugin, 'get_module_tools'):
          commands = plugin.get_module_tools()
          if cmd_name in commands:
            return plugin, commands[cmd_name], info
      return None, None, None

    for plugin in self.module_pm.get_plugins():
      info = plugin.get_module_info()
      if info and hasattr(plugin, 'get_module_tools'):
        commands = plugin.get_module_tools()
        if command_name in commands:
          return plugin, commands[command_name], info
    return None, None, None

  def get_all_commands(self) -> Dict[str, Dict]:
    """Get all available commands in hierarchical format."""
    self.load_all_plugins()
    result = {}

    for plugin in self.module_pm.get_plugins():
      info = plugin.get_module_info()
      if not info or not hasattr(plugin, 'get_module_tools'):
        continue

      module_entry = {
        "module_info": info,
        "list_of_tools": []
      }

      commands = plugin.get_module_tools()
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

        module_entry["list_of_tools"].append({
          "tool_name": cmd_name,
          "tool_description": cmd_def.description,
          "tool_callable": cmd_def.callable,
          "arguments": arguments_info
        })

      result[info.name] = module_entry
    return result

  def get_pattern_by_name(self, name: str):
    """Get a tool pattern plugin by name."""
    self.load_all_plugins()
    return self._find_plugin_by_name(self.pattern_pm, 'get_pattern_info', name)

  def get_default_pattern(self):
    """Get the default pattern plugin."""
    self.load_all_plugins()
    patterns = list(self.pattern_pm.get_plugins())
    return patterns[0] if patterns else None


  # AGENTS
  def register_agent(
    self,
    agent_class: Type[BaseAgent],
    name: Optional[str] = None,
    description: Optional[str] = None,
    required_args: Optional[List[str]] = None
  ) -> None:
    """
    Register an agent class programmatically without using pluggy.
    
    This allows developers to register custom agents directly:
        registry.register(MyCustomAgent, name="my_agent", description="My custom agent")
    
    Args:
        agent_class: The agent class to register (must inherit from BaseAgent)
        name: The name to register the agent under (defaults to class name)
        description: Description of the agent (defaults to class docstring)
        required_args: Optional list of required arguments for the agent
    
    Raises:
        ValueError: If the agent class is invalid or name is already registered
    """
    # Validate that the agent class inherits from BaseAgent
    if not issubclass(agent_class, BaseAgent):
      raise ValueError(f"Agent class {agent_class.__name__} must inherit from BaseAgent")
    
    # Use class name if no name provided
    if name is None:
      name = agent_class.__name__
    
    # Use class docstring if no description provided
    if description is None:
      description = agent_class.get_description()
    
    # Check if name is already registered
    if name in self._registered_agents:
      logger.warning(f"Agent '{name}' is already registered, overwriting")
    
    # Create AgentInfo and store it
    agent_info = AgentInfo(
      name=name,
      description=description,
      agent_class=agent_class,
      required_args=required_args
    )
    
    self._registered_agents[name] = agent_info
    logger.info(f"Registered agent '{name}' ({agent_class.__name__})")

  def get_agent_class(self, agent_name: str) -> Optional[Type[BaseAgent]]:
    """Get the agent class for a specific agent name.
    
    Programmatically registered agents take priority over pluggy agents
    when the same name is used.
    """
    # Load all agents from all sources
    all_agents = self.get_agents()
    
    # Search through all agents (programmatic ones are listed first, giving them priority)
    for agent_info in all_agents:
      if agent_info.name == agent_name:
        logger.debug(f"Found agent class {agent_info.agent_class.__name__} for {agent_name}")
        return agent_info.agent_class

    logger.debug(f"No agent class found for {agent_name}")
    return None

  def get_agents(self) -> List[AgentInfo]:
    """Get all available agents from all sources.
    
    Returns both programmatically registered agents and pluggy-based agents.
    Programmatically registered agents are listed first, giving them priority
    when multiple agents share the same name.
    """
    self.load_all_plugins()
    agents = []
    
    # Add programmatically registered agents first (priority)
    agents.extend(self._registered_agents.values())
    
    # Add pluggy agents
    try:
      pluggy_agents = self.agent_pm.hook.get_agent_info()
      # Only add pluggy agents that don't conflict with programmatic ones
      programmatic_names = set(self._registered_agents.keys())
      for agent_info in pluggy_agents:
        if agent_info.name not in programmatic_names:
          agents.append(agent_info)
        else:
          logger.debug(f"Pluggy agent '{agent_info.name}' shadowed by programmatic registration")
    except Exception as e:
      logger.warning(f"Failed collecting agent info: {e}")
    return agents

  def get_agent_info_by_name(self, agent_name: str) -> Optional[AgentInfo]:
    """Get agent info for a specific agent by name.
    
    Searches through all available agents (both programmatic and pluggy).
    Programmatically registered agents take priority over pluggy agents
    when the same name is used.
    """
    agents = self.get_agents()
    for agent_info in agents:
      if agent_info.name == agent_name:
        return agent_info
    return None