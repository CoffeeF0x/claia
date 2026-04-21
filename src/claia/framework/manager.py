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

Extensions are lazy-loaded: definitions/metadata are discovered first
without instantiation, allowing each plugin's declared ``ParamSpec``
list to be collected for dynamic settings. Full instantiation occurs
when the extension is first accessed.
"""

import pluggy
import logging
import importlib.metadata as metadata
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Type, Any, Tuple

from .hooks import (
  ArchitectureHooks, DeploymentHooks, SolverHooks, DefinitionHooks,
  PatternHooks, ProtocolHooks, ToolModuleHooks, AgentHooks,
  DeploymentInfo, SolverInfo, ModelDefinition, ArchitectureInfo, AgentInfo
)
from claia.core.models.base import BaseModel
from claia.core.plugins.base import ParamScope, ParamSpec
from .agents.base import BaseAgent



########################################################################
#                              CONSTANTS                               #
########################################################################
DEFAULT_SOLVER = "default"

# Map entry point group -> plugin info method name. All info objects
# returned by these methods share the ``ExtensionInfo`` shape and
# advertise their parameters via ``ExtensionInfo.params`` (a list of
# ``ParamSpec``). The Manager filters constructor kwargs against the
# ``INIT``-scoped specs and surfaces the specs themselves so Settings
# can build CLI flags / env lookups dynamically.
INFO_METHOD_BY_GROUP: Dict[str, Optional[str]] = {
  'claia.architectures': 'get_architecture_info',   # -> ArchitectureInfo
  'claia.deployments': 'get_deployment_info',       # -> DeploymentInfo
  'claia.solvers': 'get_solver_info',               # -> SolverInfo
  'claia.definitions': None,                        # -> Dict[str, ModelDefinition] via hook
  'claia.tool_patterns': 'get_pattern_info',        # -> PatternInfo
  'claia.tool_protocols': 'get_protocol_info',      # -> ProtocolInfo
  'claia.tool_modules': 'get_module_info',          # -> ToolModuleInfo
  'claia.agents': 'get_agent_info',                 # -> AgentInfo
}


########################################################################
#                            DATA CLASSES                              #
########################################################################
@dataclass
class LazyPluginEntry:
  """Represents a discovered but not-yet-instantiated plugin."""
  name: str                    # Entry point name
  group: str                   # Entry point group (e.g., 'claia.tool_modules')
  entry_point: Any             # The entry point object
  plugin_class: Type = None    # Loaded class (after load())
  info: Any = None             # Plugin info object (from get_*_info())
  instance: Any = None         # Instantiated plugin (lazy)
  params: List[ParamSpec] = field(default_factory=list)  # Cached ParamSpecs



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
  
  Extensions are lazy-loaded: ``discover_plugins()`` collects metadata
  without instantiation, allowing ``ParamSpec`` declarations to be
  collected for dynamic settings. Full instantiation occurs when
  ``load_all_plugins()`` is called with settings.
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

    # Lazy loading state
    self._lazy_plugins: Dict[str, List[LazyPluginEntry]] = {}  # group -> list of entries
    self._plugins_discovered = False
    self._plugins_loaded = False
    logger.debug("Manager initialized")


  ######################################################################
  #                         LAZY LOADING                               #
  ######################################################################
  def discover_plugins(self) -> None:
    """
    Discover all plugins from entry points without fully instantiating them.

    This method:
    1. Loads each plugin class from entry points
    2. Creates a temporary no-arg instance to introspect its info
    3. Extracts ``ParamSpec`` declarations and stores them for later use
    4. Does NOT register the plugin with pluggy yet

    This allows collecting parameter specs before settings are fully
    loaded, breaking the circular dependency between settings and
    extensions.
    """
    if self._plugins_discovered:
      logger.debug("Plugins already discovered")
      return

    groups = list(INFO_METHOD_BY_GROUP.keys())

    for group in groups:
      self._lazy_plugins[group] = []

      for ep in metadata.entry_points().select(group=group):
        entry = LazyPluginEntry(
          name=ep.name,
          group=group,
          entry_point=ep
        )

        try:
          entry.plugin_class = ep.load()

          try:
            temp_instance = entry.plugin_class()

            info_method = INFO_METHOD_BY_GROUP.get(group)
            if info_method and hasattr(temp_instance, info_method):
              try:
                entry.info = getattr(temp_instance, info_method)()
                params = getattr(entry.info, 'params', None) or []
                entry.params = list(params)
              except Exception as e:
                logger.debug(f"Could not get info for {ep.name}: {e}")

            # Architectures carry their RUNTIME generation knobs on the
            # model class itself (BaseModel.runtime_params), not in
            # ArchitectureInfo. Pull those in so they're discoverable as
            # extension params (CLI flags, dispatch-time filtering)
            # without forcing every architecture to redeclare them.
            # We mirror the merged list back onto entry.info.params so
            # consumers that read ``ArchitectureInfo`` directly (e.g.
            # ``Registry._run_stream``) also see the runtime specs.
            if group == "claia.architectures" and hasattr(temp_instance, "get_model_class"):
              try:
                model_cls = temp_instance.get_model_class()
                model_runtime = getattr(model_cls, "runtime_params", None) or []
                seen_names = {p.name for p in entry.params}
                for spec in model_runtime:
                  if spec.name not in seen_names:
                    entry.params.append(spec)
                    seen_names.add(spec.name)
                if entry.info is not None and hasattr(entry.info, 'params'):
                  try:
                    entry.info.params = list(entry.params)
                  except Exception:
                    pass
              except Exception as e:
                logger.debug(f"Could not collect runtime_params for {ep.name}: {e}")

          except Exception as e:
            logger.debug(f"Could not create temp instance for {ep.name}: {e}")

        except Exception as e:
          logger.warning(f"Failed to load plugin class {ep.name} from {group}: {e}")
          continue

        self._lazy_plugins[group].append(entry)
        logger.debug(f"Discovered {group} plugin: {ep.name}")

    self._plugins_discovered = True
    logger.info(f"Discovered plugins from {len(groups)} groups")


  def get_all_plugin_params(self) -> Dict[str, List[ParamSpec]]:
    """
    Return every discovered plugin's declared ``ParamSpec`` list.

    Keys are ``"{group}:{name}"`` strings, values are (possibly empty)
    lists of ``ParamSpec`` objects. Useful for diagnostics and for
    settings code that needs to know which plugin owns a given param.
    """
    self.discover_plugins()
    result: Dict[str, List[ParamSpec]] = {}
    for group, entries in self._lazy_plugins.items():
      for entry in entries:
        key = f"{group}:{entry.name}"
        result[key] = list(entry.params)
    return result


  def get_extension_params(self, scope: Optional[ParamScope] = None) -> List[ParamSpec]:
    """
    Return the flat list of ``ParamSpec`` objects declared by all
    discovered extensions.

    When the same parameter ``name`` is declared by multiple plugins,
    the first occurrence wins (subsequent declarations are treated as
    aliases and ignored for metadata purposes). Settings/CLI layers use
    this list to build flags, env lookups, help text, etc.

    Args:
      scope: If provided, only return specs whose scope matches.
    """
    self.discover_plugins()
    seen: Dict[str, ParamSpec] = {}
    for _, entries in self._lazy_plugins.items():
      for entry in entries:
        for spec in entry.params:
          if scope is not None and spec.scope != scope:
            continue
          if spec.name not in seen:
            seen[spec.name] = spec
    return list(seen.values())


  def load_all_plugins(self, **kwargs) -> None:
    """
    Load all plugins from entry points.
    
    Uses lazy loading: if plugins were already discovered via discover_plugins(),
    uses the cached entries and instantiates them with the provided kwargs.
    Otherwise, discovers and loads in one step.
    """
    if self._plugins_loaded:
      logger.debug("Plugins already loaded")
      return

    # Ensure plugins are discovered first
    self.discover_plugins()

    try:
      # Load definition plugins first (they're optional)
      self._load_plugins(group='claia.definitions', pm=self.definition_pm, label='definition', allow_empty=True, ctor_kwargs=kwargs)

      # Load tool plugins (pass in kwargs; each plugin receives only its INIT-scoped params)
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
    """Load plugins securely by filtering ctor kwargs against INIT ParamSpecs.

    Uses the lazy plugin entries discovered by ``discover_plugins()``.
    Each plugin is instantiated with only the kwargs whose names match
    an ``INIT``-scoped ``ParamSpec`` declared by that plugin.
    """
    loaded_count = 0

    try:
      entries = self._lazy_plugins.get(group, [])

      for entry in entries:
        try:
          cls = entry.plugin_class
          if cls is None:
            logger.warning(f"No plugin class loaded for {entry.name}")
            continue

          inst = None

          filtered_kwargs: Dict[str, Any] = {}
          if entry.params and ctor_kwargs:
            filtered_kwargs = self.filter_init_kwargs(ctor_kwargs, entry.params)

          # Required-kwargs validation is deliberately NOT enforced
          # here — most plugin classes (Architectures, Deployments,
          # Solvers, Agents) take no constructor args and merely return
          # a model/info class. The "required" credentials apply when
          # the underlying model is actually constructed at request
          # time, which is where Registry/Manager call sites should
          # invoke ``validate_required_init_kwargs`` if they want to
          # surface a clean error instead of letting the model class
          # raise on its own.
          if filtered_kwargs:
            try:
              inst = cls(**filtered_kwargs)
            except Exception as e:
              logger.debug(f"Instantiating {label} plugin {entry.name} with kwargs failed: {e}")
              try:
                inst = cls()
              except Exception as e2:
                logger.warning(f"Failed to instantiate {label} plugin {entry.name}: {e2}")
                continue
          else:
            try:
              inst = cls()
            except Exception as e:
              logger.warning(f"Failed to instantiate {label} plugin {entry.name}: {e}")
              continue

          entry.instance = inst

          pm.register(inst)
          loaded_count += 1
          logger.debug(f"Loaded {label} plugin: {entry.name} from {entry.entry_point.value}")

        except Exception as e:
          logger.warning(f"Failed to load {label} plugin {entry.name}: {e}")

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

  @staticmethod
  def filter_init_kwargs(kwargs: Dict[str, Any], params: Optional[List[ParamSpec]]) -> Dict[str, Any]:
    """Return the coerced subset of ``kwargs`` matching a plugin's INIT specs.

    Any kwarg whose name does not match an ``INIT``-scoped ``ParamSpec``
    in ``params`` is dropped. Matching values are coerced to the spec's
    declared type and validated against ``choices`` (if present). Coerce
    or choice failures are logged as warnings and the offending value is
    dropped — the plugin's own constructor default applies.

    ``required=True`` is NOT enforced here (filtering is a partial
    operation and may be called before all sources have been merged).
    Use :meth:`validate_required_init_kwargs` immediately before
    instantiation to enforce required specs.
    """
    return _filter_by_scope(kwargs, params, ParamScope.INIT, label="init")

  @staticmethod
  def filter_runtime_kwargs(kwargs: Dict[str, Any], params: Optional[List[ParamSpec]]) -> Dict[str, Any]:
    """Return the coerced subset of ``kwargs`` matching a plugin's RUNTIME specs.

    Mirrors :meth:`filter_init_kwargs` for per-call generation
    parameters. Defaults from the ParamSpecs are NOT applied here — use
    :meth:`BaseModel.update_settings` to overlay declared defaults.
    """
    return _filter_by_scope(kwargs, params, ParamScope.RUNTIME, label="runtime")

  @staticmethod
  def validate_required_init_kwargs(kwargs: Dict[str, Any], params: Optional[List[ParamSpec]]) -> List[str]:
    """Return the names of any ``required=True`` INIT specs missing from ``kwargs``.

    Empty-string and ``None`` values count as missing. Callers should
    raise (or skip instantiation) if the returned list is non-empty.
    """
    if not params:
      return []
    missing: List[str] = []
    for spec in params:
      if spec.scope != ParamScope.INIT or not spec.required:
        continue
      value = kwargs.get(spec.name)
      if value is None or value == "":
        missing.append(spec.name)
    return missing

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
    """
    Get all available architecture plugins and their info keyed by name.

    The returned ``ArchitectureInfo.params`` lists are augmented with the
    model class's ``runtime_params`` (collected during ``discover_plugins``)
    so dispatch-time consumers see both INIT and RUNTIME specs for the
    architecture without having to reach into the lazy plugin entries.
    """
    self.load_all_plugins()
    all_arch = self._collect_info_dict(self.architecture_pm, 'get_architecture_info')

    cached_by_name: Dict[str, List[ParamSpec]] = {}
    for entry in self._lazy_plugins.get("claia.architectures", []):
      info_name = getattr(entry.info, 'name', None) if entry.info else None
      if info_name:
        cached_by_name[info_name] = list(entry.params)

    for name, info in all_arch.items():
      cached = cached_by_name.get(name)
      if cached and hasattr(info, 'params'):
        seen = {p.name for p in (info.params or [])}
        merged = list(info.params or [])
        for spec in cached:
          if spec.name not in seen:
            merged.append(spec)
            seen.add(spec.name)
        try:
          info.params = merged
        except Exception:
          pass

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
    title: Optional[str] = None,
    description: Optional[str] = None,
    params: Optional[List[ParamSpec]] = None,
  ) -> None:
    """
    Register an agent class programmatically without using pluggy.

    This allows developers to register custom agents directly:
        registry.register(MyCustomAgent, name="my_agent", description="My custom agent")

    Args:
        agent_class: The agent class to register (must inherit from BaseAgent).
        name: The name to register the agent under (defaults to class name).
        title: Human-readable display name (defaults to class name).
        description: Description of the agent (defaults to class docstring).
        params: Optional list of ``ParamSpec`` declarations for the
          agent. ``INIT``-scoped specs are used to filter construction
          kwargs; ``RUNTIME``-scoped specs describe per-call params.

    Raises:
        ValueError: If the agent class does not inherit from BaseAgent.
    """
    if not issubclass(agent_class, BaseAgent):
      raise ValueError(f"Agent class {agent_class.__name__} must inherit from BaseAgent")

    if name is None:
      name = agent_class.__name__

    if title is None:
      title = agent_class.__name__

    if description is None:
      description = agent_class.get_description()

    if name in self._registered_agents:
      logger.warning(f"Agent '{name}' is already registered, overwriting")

    agent_info = AgentInfo(
      name=name,
      title=title,
      description=description,
      agent_class=agent_class,
      params=list(params) if params else [],
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


########################################################################
#                  KWARG COERCION / VALIDATION HELPERS                 #
########################################################################
class _CoerceFail:
  """Sentinel returned from ``_coerce_value`` when conversion fails."""
  __slots__ = ()


_COERCE_FAIL = _CoerceFail()
_TRUTHY = {"true", "1", "yes", "on", "y", "t"}
_FALSY = {"false", "0", "no", "off", "n", "f"}


def _mask_for_log(value: Any, spec: ParamSpec) -> str:
  """
  Mask ``value`` for inclusion in log output if ``spec`` is marked secret.

  Returns the original value otherwise. Used by ``_filter_by_scope``
  warnings so a malformed API token never lands in plaintext logs.
  """
  if not getattr(spec, 'secret', False):
    return value
  s = str(value)
  if not s:
    return "***"
  return "***" + s[-4:] if len(s) > 4 else "***"


def _coerce_value(value: Any, target: type) -> Any:
  """Best-effort coerce ``value`` to ``target``. Returns ``_COERCE_FAIL`` on failure."""
  if value is None:
    return None
  if target is None:
    return value
  if isinstance(value, target) and not (target is int and isinstance(value, bool)):
    return value
  try:
    if target is bool:
      if isinstance(value, str):
        v = value.strip().lower()
        if v in _TRUTHY:
          return True
        if v in _FALSY:
          return False
        return _COERCE_FAIL
      return bool(value)
    if target is int:
      if isinstance(value, str):
        return int(value.strip())
      return int(value)
    if target is float:
      if isinstance(value, str):
        return float(value.strip())
      return float(value)
    if target is str:
      return str(value)
    return target(value)
  except (TypeError, ValueError):
    return _COERCE_FAIL


def _filter_by_scope(
  kwargs: Dict[str, Any],
  params: Optional[List[ParamSpec]],
  scope: ParamScope,
  label: str,
) -> Dict[str, Any]:
  """
  Return the subset of ``kwargs`` matching ``params`` of the given scope.

  Coerces each value to its spec's declared type and validates
  ``choices``. Coerce/choice failures are logged at WARNING and the
  value is dropped (so the plugin's own default applies).
  """
  if not params:
    return {}

  scoped = {p.name: p for p in params if p.scope == scope}
  if not scoped:
    return {}

  filtered: Dict[str, Any] = {}
  for name, spec in scoped.items():
    if name not in kwargs:
      continue
    raw = kwargs[name]
    coerced = _coerce_value(raw, spec.type or str)
    if coerced is _COERCE_FAIL:
      logger.warning(
        f"Dropping {label} kwarg {name}={_mask_for_log(raw, spec)!r}: "
        f"could not coerce to {(spec.type or str).__name__}"
      )
      continue
    if spec.choices is not None and coerced not in spec.choices:
      logger.warning(
        f"Dropping {label} kwarg {name}={_mask_for_log(coerced, spec)!r}: "
        f"not in allowed choices {spec.choices}"
      )
      continue
    filtered[name] = coerced

  if logger.isEnabledFor(logging.DEBUG):
    undeclared = [k for k in kwargs if k not in scoped]
    if undeclared:
      logger.debug(f"Dropping undeclared {label} kwargs: {sorted(undeclared)}")
  return filtered


# Module-level aliases so callers don't have to go through the Manager
# class (and aren't affected by Manager being monkeypatched in tests).
filter_init_kwargs = Manager.filter_init_kwargs
filter_runtime_kwargs = Manager.filter_runtime_kwargs
validate_required_init_kwargs = Manager.validate_required_init_kwargs