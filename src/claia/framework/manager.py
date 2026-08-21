"""
Manager for the CLAIA system.

This module handles loading and coordinating all plugin types:
- Model architectures (implement specific AI models)
- Model deployments (handle deployment methods)
- Model definitions (provide model metadata)
- Tool protocols (handle tool execution)
- Tool modules (provide tool implementations)
- Agents (orchestrate model and tool calls)

Extensions are lazy-loaded: definitions/metadata are discovered first
without instantiation, allowing each plugin's declared ``ParamSpec``
list to be collected for dynamic settings. Full instantiation occurs
when the extension is first accessed. Agents are never instantiated —
discovery records the class and fills ``AgentInfo.agent_class``.
"""

import logging
import importlib.metadata as metadata
from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Type

from ..core.definitions.model_definition import ModelDefinition, merge_model_definitions
from ..core.models.base import BaseModel
from ..core.plugins.base import ArchitectureInfo, DeploymentInfo, ParamScope, ParamSpec
from .agents.base import AgentInfo, BaseAgent



########################################################################
#                              CONSTANTS                               #
########################################################################
# All entry point groups the manager cares about. Plugins declare
# their metadata via a class-level ``info`` attribute (subclass of
# ``ExtensionInfo``); the ``info.params`` list drives Settings,
# CLI flags, and init-kwarg filtering. Definition plugins are the one
# exception — they don't carry an ``info`` object and expose their
# metadata via ``get_definitions()`` instead.
PLUGIN_GROUPS: Tuple[str, ...] = (
  'claia.architectures',
  'claia.deployments',
  'claia.definitions',
  'claia.tool_protocols',
  'claia.tool_modules',
  'claia.agents',
)


########################################################################
#                            DATA CLASSES                              #
########################################################################
@dataclass
class PluginEntry:
  """A discovered plugin and its cached metadata.

  Produced by :meth:`Manager.discover_plugins` without instantiation:
  the class reference and ``info`` object are read from the plugin
  class, never from an instance. Instantiation happens later in
  :meth:`Manager.load_all_plugins` once the full kwarg environment
  (Settings) is available. Agent entries stay uninstantiated.
  """
  name: str                    # Entry point name
  group: str                   # Entry point group (e.g. ``claia.tool_modules``)
  entry_point: Any             # Raw ``importlib.metadata`` entry point
  plugin_class: Type = None    # Loaded plugin class
  info: Any = None             # Class-level ``info`` (subclass of ExtensionInfo)
  instance: Any = None         # Pure plugin instance (ABC subclass), set at load time
  params: List[ParamSpec] = field(default_factory=list)  # Flattened ParamSpec list



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
  - Model: Architecture, Deployment, Definition plugins
  - Tools: Protocol, ToolModule plugins
  - Agents: Agent plugins

  Extensions are lazy-loaded: ``discover_plugins()`` collects metadata
  without instantiation, allowing ``ParamSpec`` declarations to be
  collected for dynamic settings. Full instantiation occurs when
  ``load_all_plugins()`` is called with settings.
  """

  def __init__(self):
    """Initialize the manager."""
    # Programmatically registered agents
    self._registered_agents: Dict[str, AgentInfo] = {}

    # group -> {info.name (or entry-point name): PluginEntry}
    self._lazy_plugins: Dict[str, Dict[str, PluginEntry]] = {}
    self._plugins_discovered = False
    self._plugins_loaded = False
    logger.debug("Manager initialized")


  ######################################################################
  #                         LAZY LOADING                               #
  ######################################################################
  def discover_plugins(self) -> None:
    """
    Discover all plugins from entry points without instantiating them.

    Two-phase loading relies on reading class-level metadata here and
    deferring instantiation to :meth:`load_all_plugins`. This is what
    breaks the otherwise-circular dependency between Settings (which
    needs to know every declared ``ParamSpec``) and plugins (which
    need Settings to be constructed).

    Steps per entry point:

    1. Load the class (unavoidable).
    2. For agents, require a ``BaseAgent`` subclass; skip others with
       a warning. Fill ``info.agent_class`` from the loaded class.
    3. Read ``cls.info`` (subclass of ``ExtensionInfo``); no instance
       is ever created during discovery. Architectures are expected
       to declare their full param contract — both INIT (credentials,
       endpoints) and RUNTIME (generation knobs like ``temperature``)
       — directly on ``ArchitectureInfo.params``.
    4. Store the :class:`PluginEntry` keyed by ``info.name`` (falling
       back to the entry-point name). First-in-wins on collisions.
    """
    if self._plugins_discovered:
      logger.debug("Plugins already discovered")
      return

    total_discovered = 0
    total_secrets = 0

    for group in PLUGIN_GROUPS:
      self._lazy_plugins[group] = {}

      for ep in metadata.entry_points().select(group=group):
        entry = PluginEntry(name=ep.name, group=group, entry_point=ep)

        try:
          entry.plugin_class = ep.load()
        except Exception as e:
          logger.warning(f"Failed to load plugin class {ep.name} from {group}: {e}")
          continue

        if group == 'claia.agents':
          cls = entry.plugin_class
          if not (isinstance(cls, type) and issubclass(cls, BaseAgent)):
            logger.warning(
              f"Skipping {ep.name} from {group}: expected a BaseAgent subclass, got {cls!r}"
            )
            continue

        self._populate_entry_metadata(entry)

        if group == 'claia.agents' and entry.info is not None:
          entry.info.agent_class = entry.plugin_class

        key = getattr(entry.info, 'name', None) or entry.name
        if key in self._lazy_plugins[group]:
          logger.warning(
            f"Skipping {group}:{ep.name}; name {key!r} already registered (first-in wins)"
          )
          continue

        self._log_discovered_entry(entry)
        total_secrets += sum(1 for p in entry.params if getattr(p, 'secret', False))

        self._lazy_plugins[group][key] = entry
        total_discovered += 1

    self._plugins_discovered = True
    logger.info(
      f"Discovered {total_discovered} plugin(s) across {len(PLUGIN_GROUPS)} group(s) "
      f"({total_secrets} secret parameter(s))"
    )

  # ------------------------------------------------------------------
  # Discovery helpers
  # ------------------------------------------------------------------
  def _populate_entry_metadata(self, entry: PluginEntry) -> None:
    """Read ``entry.info`` and flatten ``entry.params`` from the class.

    Plugins are required to expose metadata through a class-level
    ``info`` attribute; definition providers are the one exception
    (they publish their metadata via ``get_definitions()``, so
    ``info`` stays ``None`` and their params list stays empty).

    Architectures declare their full param contract — both INIT
    (credentials, endpoints) and RUNTIME (generation knobs) — on the
    ``ArchitectureInfo`` itself. There is no fold-in from the model
    class; the architecture plugin is the single source of truth.
    """
    cls = entry.plugin_class
    class_info = getattr(cls, 'info', None)
    if class_info is not None and not isinstance(class_info, (property, classmethod, staticmethod)):
      entry.info = class_info

    entry.params = list(getattr(entry.info, 'params', None) or [])

  @staticmethod
  def _log_discovered_entry(entry: PluginEntry) -> None:
    """Emit a compact log line for a freshly discovered plugin.

    Secret-scoped parameters are surfaced at INFO level — without
    values — so operators can see at startup which credentials each
    plugin will consume. Non-secret parameters are logged at DEBUG to
    avoid noisy startup output.
    """
    info_name = getattr(entry.info, 'name', None) or entry.name
    title = getattr(entry.info, 'title', None) or info_name

    secret_params = [p for p in entry.params if getattr(p, 'secret', False)]
    other_params = [p for p in entry.params if not getattr(p, 'secret', False)]

    if secret_params:
      names = ", ".join(sorted(p.name for p in secret_params))
      logger.info(
        f"Discovered {entry.group}:{info_name} ({title}) "
        f"— declares secret param(s): {names}"
      )
    else:
      logger.debug(f"Discovered {entry.group}:{info_name} ({title})")

    if other_params and logger.isEnabledFor(logging.DEBUG):
      names = ", ".join(sorted(p.name for p in other_params))
      logger.debug(f"  non-secret params for {entry.group}:{info_name}: {names}")


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
      for key, entry in entries.items():
        result[f"{group}:{key}"] = list(entry.params)
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
    for entries in self._lazy_plugins.values():
      for entry in entries.values():
        for spec in entry.params:
          if scope is not None and spec.scope != scope:
            continue
          if spec.name not in seen:
            seen[spec.name] = spec
    return list(seen.values())


  def load_all_plugins(self, **kwargs) -> None:
    """
    Load all plugins from entry points.

    Uses lazy loading: if plugins were already discovered via
    discover_plugins(), uses the cached entries and instantiates each
    class with no arguments. Otherwise, discovers and loads in one
    step. ``kwargs`` is accepted for the public load API and consumed
    later at dispatch via ``ParamSpec`` filtering.
    """
    if self._plugins_loaded:
      logger.debug("Plugins already loaded")
      return

    # Ensure plugins are discovered first
    self.discover_plugins()

    try:
      # Load definition plugins first (they're optional)
      self._load_plugins(group='claia.definitions', label='definition', allow_empty=True)

      # Load tool plugins (instances take no constructor args)
      self._load_plugins(group='claia.tool_protocols', label='protocol', allow_empty=True)
      self._load_plugins(group='claia.tool_modules', label='module', allow_empty=True)

      # Hand the freshly-loaded native tool modules to any protocol
      # that opts in via ``bind_tool_modules`` (currently only the
      # simple protocol). Done before ``start()`` so a protocol's
      # startup logic can already see its inventory.
      self._bind_native_tools_to_protocols()

      # Fire ``start()`` on each loaded protocol so session-bearing
      # implementations (MCP, remote RPC, etc.) can open their
      # resources once plugins are wired in. Any failure logs and is
      # skipped; the protocol still registers so other static
      # protocols (simple) don't go down with it.
      self._start_protocols()

      # Agent plugins are discovered only — never instantiated.
      self._load_plugins(group='claia.agents', label='agent', allow_empty=True)

      # Load model plugins (required)
      self._load_plugins(group='claia.architectures', label='architecture', allow_empty=False)
      self._load_plugins(group='claia.deployments', label='deployment', allow_empty=False)

      self._plugins_loaded = True
      logger.info("All plugins loaded")

    except Exception as e:
      logger.error(f"Error loading plugins: {e}")
      raise RuntimeError(f"Failed to load plugins: {e}")


  ######################################################################
  #                               UTILS                                #
  ######################################################################
  def _iter_entries(self, group: str):
    """Yield :class:`PluginEntry` objects for ``group``."""
    yield from self._lazy_plugins.get(group, {}).values()

  def _iter_instances(self, group: str):
    """Yield instantiated plugins for ``group`` (skips unloaded entries)."""
    for entry in self._iter_entries(group):
      if entry.instance is not None:
        yield entry.instance

  def _load_plugins(self, group: str, label: str, allow_empty: bool = False) -> None:
    """Instantiate discovered plugins and store them on their entries.

    Plugin classes are stateless metadata + factory objects: they
    expose an ``info`` attribute and (for architectures) a
    ``get_model_class`` factory, but don't own the credentials or
    runtime state themselves. INIT-scoped ``ParamSpec`` entries on
    ``info.params`` describe what the *downstream* object (a model
    instance, an outbound API call, ...) consumes; the registry
    filters kwargs against those specs at dispatch time. The plugin
    itself is always instantiated with no arguments.

    Agent plugins are never instantiated — discovery already recorded
    the class and filled ``info.agent_class``.
    """
    loaded_count = 0

    try:
      if group == 'claia.agents':
        loaded_count = len(self._lazy_plugins.get(group, {}))
      else:
        for entry in self._iter_entries(group):
          try:
            inst = self._instantiate_plugin(entry.plugin_class, entry.name, label)
            if inst is None:
              continue

            entry.instance = inst
            loaded_count += 1
            ep_value = getattr(entry.entry_point, 'value', None) or entry.name
            logger.debug(f"Loaded {label} plugin: {entry.name} from {ep_value}")

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

  # ------------------------------------------------------------------
  # Protocol lifecycle
  # ------------------------------------------------------------------
  def iter_protocol_instances(self):
    """Yield the plain ``BaseProtocol`` instances for loaded protocols.

    ``Registry._rebuild_tool_index`` consumes this to collect each
    protocol's ``ToolReference`` list.
    """
    yield from self._iter_instances('claia.tool_protocols')

  def _bind_native_tools_to_protocols(self) -> None:
    """Hand the loaded native ``BaseToolModule`` instances to any
    protocol that opts in to native-module binding.

    Duck-types on the presence of ``bind_tool_modules`` so third-party
    protocols that want native-module access can opt in without a new
    ABC method.

    Errors from any one protocol log + are swallowed so a malfunctioning
    binder cannot block other protocols from coming up.
    """
    modules = [
      entry.instance
      for entry in self._iter_entries('claia.tool_modules')
      if entry.instance is not None
    ]
    self._dispatch_protocol_hook(
      'bind_tool_modules',
      lambda hook: hook(modules),
      failure_tail='skipping',
    )

  def _start_protocols(self) -> None:
    """Call ``start()`` on every loaded protocol, swallowing errors.

    The default ``BaseProtocol.start`` is a no-op. Session-bearing
    protocols (MCP) open their connections here. A single protocol's
    failure must not prevent other protocols from running.
    """
    self._dispatch_protocol_hook(
      'start',
      lambda hook: hook(),
      failure_tail='continuing with partial inventory',
    )

  def stop_protocols(self) -> None:
    """Call ``stop()`` on every loaded protocol.

    Exposed on ``Manager`` so the ``Registry`` can tear down external
    sessions during application shutdown. Errors are logged and
    swallowed — teardown should never crash the caller.
    """
    self._dispatch_protocol_hook(
      'stop',
      lambda hook: hook(),
      failure_tail='continuing teardown',
    )

  def refresh_protocols(self) -> None:
    """Call ``refresh()`` on every loaded protocol.

    Triggered by registry callers that need to react to dynamic
    inventory changes (e.g. an MCP ``notifications/tools/list_changed``).
    Errors log and are skipped; the registry rebuilds its index from
    the post-refresh ``get_tool_references()`` outputs separately.
    """
    self._dispatch_protocol_hook(
      'refresh',
      lambda hook: hook(),
      failure_tail='keeping prior inventory',
    )

  def _dispatch_protocol_hook(
    self,
    hook_name: str,
    invoke: Any,
    *,
    failure_tail: str,
  ) -> None:
    """Run ``invoke(getattr(protocol, hook_name))`` across loaded protocols.

    Skips protocols that don't expose the hook (duck typing), logs and
    swallows per-protocol exceptions so a single bad protocol cannot
    take the rest of the lifecycle pass down. ``failure_tail`` is the
    contextual phrase appended to the warning message ("continuing
    teardown", "skipping", etc.).
    """
    for inst in self.iter_protocol_instances():
      hook = getattr(inst, hook_name, None)
      if not callable(hook):
        continue
      try:
        invoke(hook)
      except Exception as e:
        logger.warning(
          "Protocol %s %s() raised %s; %s",
          type(inst).__name__, hook_name, e, failure_tail,
        )

  @staticmethod
  def _instantiate_plugin(
    cls: Type,
    name: str,
    label: str,
  ) -> Optional[Any]:
    """Instantiate a plugin class with no arguments.

    Plugins are stateless factories in this codebase; any INIT kwargs
    they declare are consumed by the object the plugin constructs
    (e.g. the model instance), not by the plugin class itself.
    Returns ``None`` if instantiation fails so the caller can skip
    the entry with a warning rather than aborting all plugin loading.
    """
    try:
      return cls()
    except Exception as e:
      logger.warning(f"Failed to instantiate {label} plugin {name}: {e}")
      return None

  # ------------------------------------------------------------------
  # Kwarg coercion / validation
  #
  # These live on the Manager class (rather than as free functions) so
  # every layer that needs to reason about plugin params — Registry at
  # dispatch time, Settings at config-load time — has a single source
  # of truth reachable via ``registry.manager.<method>``.
  # ------------------------------------------------------------------
  _COERCE_FAIL: ClassVar[object] = object()
  _TRUTHY: ClassVar[frozenset] = frozenset({"true", "1", "yes", "on", "y", "t"})
  _FALSY: ClassVar[frozenset] = frozenset({"false", "0", "no", "off", "n", "f"})

  @staticmethod
  def coerce_value(value: Any, target: type) -> Any:
    """Best-effort coerce ``value`` to ``target``.

    Returns ``Manager._COERCE_FAIL`` on failure so callers can
    distinguish "coercion could not be performed" from a legitimate
    falsy result (``0``, ``""``, ``False``, ...).
    """
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
          if v in Manager._TRUTHY:
            return True
          if v in Manager._FALSY:
            return False
          return Manager._COERCE_FAIL
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
      return Manager._COERCE_FAIL

  @staticmethod
  def _mask_for_log(value: Any, spec: ParamSpec) -> Any:
    """Return a log-safe rendering of ``value`` for ``spec``.

    When ``spec.secret`` is True the value is shortened to ``***<last4>``
    so a malformed API token never lands in plaintext warnings.
    """
    if not getattr(spec, 'secret', False):
      return value
    s = str(value)
    if not s:
      return "***"
    return "***" + s[-4:] if len(s) > 4 else "***"

  @staticmethod
  def _filter_by_scope(
    kwargs: Dict[str, Any],
    params: Optional[List[ParamSpec]],
    scope: ParamScope,
    label: str,
  ) -> Dict[str, Any]:
    """Shared implementation behind ``filter_init_kwargs`` / ``filter_runtime_kwargs``.

    Returns the subset of ``kwargs`` matching ``params`` of the given
    scope, coerced to each spec's declared type and validated against
    its ``choices``. Coerce/choice failures log at WARNING and drop the
    value so the plugin's own default applies.
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
      coerced = Manager.coerce_value(raw, spec.type or str)
      if coerced is Manager._COERCE_FAIL:
        logger.warning(
          f"Dropping {label} kwarg {name}={Manager._mask_for_log(raw, spec)!r}: "
          f"could not coerce to {(spec.type or str).__name__}"
        )
        continue
      if spec.choices is not None and coerced not in spec.choices:
        logger.warning(
          f"Dropping {label} kwarg {name}={Manager._mask_for_log(coerced, spec)!r}: "
          f"not in allowed choices {spec.choices}"
        )
        continue
      filtered[name] = coerced

    if logger.isEnabledFor(logging.DEBUG):
      undeclared = [k for k in kwargs if k not in scoped]
      if undeclared:
        logger.debug(f"Dropping undeclared {label} kwargs: {sorted(undeclared)}")
    return filtered

  @staticmethod
  def filter_init_kwargs(kwargs: Dict[str, Any], params: Optional[List[ParamSpec]]) -> Dict[str, Any]:
    """Return the coerced subset of ``kwargs`` matching a plugin's INIT specs.

    Any kwarg whose name does not match an ``INIT``-scoped ``ParamSpec``
    in ``params`` is dropped. Matching values are coerced to the spec's
    declared type and validated against ``choices`` (if present). Coerce
    or choice failures log as warnings and the value is dropped — the
    plugin's own constructor default applies.

    ``required=True`` is NOT enforced here (filtering is a partial
    operation and may be called before all sources have been merged).
    Use :meth:`validate_required_init_kwargs` immediately before
    instantiation to enforce required specs.
    """
    return Manager._filter_by_scope(kwargs, params, ParamScope.INIT, label="init")

  @staticmethod
  def filter_runtime_kwargs(kwargs: Dict[str, Any], params: Optional[List[ParamSpec]]) -> Dict[str, Any]:
    """Return the coerced subset of ``kwargs`` matching a plugin's RUNTIME specs.

    Mirrors :meth:`filter_init_kwargs` for per-call generation
    parameters. Defaults from the ParamSpecs are NOT applied here — use
    :meth:`resolve_runtime_kwargs` when a fully-resolved settings dict
    is needed (e.g. right before invoking ``model.generate``).
    """
    return Manager._filter_by_scope(kwargs, params, ParamScope.RUNTIME, label="runtime")

  @staticmethod
  def resolve_runtime_kwargs(kwargs: Dict[str, Any], params: Optional[List[ParamSpec]]) -> Dict[str, Any]:
    """Return a fully-resolved RUNTIME kwargs dict for the given specs.

    Starts from the declared default of every RUNTIME-scoped
    ``ParamSpec`` in ``params``, then overlays the coerced subset of
    ``kwargs`` produced by :meth:`filter_runtime_kwargs`. The result is
    the dict a model's ``generate`` should consume directly — no
    further spec-level filtering or defaulting is required.

    First-declared-wins: when the same ``name`` appears more than once
    in ``params`` (e.g. an architecture override plus a later spread of
    ``COMMON_TEXT_RUNTIME_PARAMS``), the *first* occurrence supplies the
    default, matching :meth:`ExtensionInfo.param`'s lookup semantics.
    Downstream filtering already collapses duplicates by name, so the
    overlay step is unaffected.
    """
    if not params:
      return {}

    resolved: Dict[str, Any] = {}
    for spec in params:
      if spec.scope != ParamScope.RUNTIME:
        continue
      if spec.name in resolved:
        continue
      resolved[spec.name] = spec.default

    resolved.update(Manager.filter_runtime_kwargs(kwargs, params))
    return resolved

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
  def _find_plugin_by_name(self, group: str, info_method: str, name: str) -> Tuple[Optional[Any], Optional[Any]]:
    """Find a loaded plugin by its info.name using the given info_method.

    Returns (plugin, info) tuple; (None, None) if not found.
    """
    for inst in self._iter_instances(group):
      try:
        info = getattr(inst, info_method)()
        if info and getattr(info, 'name', None) == name:
          return inst, info
      except Exception as e:
        logger.warning(f"Failed retrieving {info_method} for plugin {inst}: {e}")
    return None, None

  def _collect_info_dict(self, group: str, info_method: str) -> Dict[str, Any]:
    """Collect instance-method info objects into a dict keyed by info.name."""
    all_items: Dict[str, Any] = {}
    for inst in self._iter_instances(group):
      try:
        info = getattr(inst, info_method)()
        if info:
          name = getattr(info, 'name', None)
          if name:
            all_items[name] = info
      except Exception as e:
        logger.warning(f"Failed collecting items via {info_method}: {e}")
    return all_items


  ######################################################################
  #                              GETTERS                               #
  ######################################################################
  # MODELS
  def get_available_architectures(self) -> Dict[str, ArchitectureInfo]:
    """
    Get all available architecture plugins and their info keyed by name.

    Each ``ArchitectureInfo.params`` already carries the plugin's full
    contract (both INIT and RUNTIME specs); there's no post-processing
    here. Dispatch-time consumers (``Registry._run_stream``) filter
    kwargs directly against this list.
    """
    self.load_all_plugins()
    all_arch = self._collect_info_dict('claia.architectures', 'get_architecture_info')
    logger.debug(f"Collected {len(all_arch)} architectures")
    return all_arch

  def get_model_class(self, architecture_name: str) -> Optional[Type[BaseModel]]:
    """Get the model class for a specific architecture by name."""
    self.load_all_plugins()
    for inst in self._iter_instances('claia.architectures'):
      try:
        info = inst.get_architecture_info()
        if info and info.name == architecture_name:
          model_class = inst.get_model_class()
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
    all_definitions: Dict[str, ModelDefinition] = {}

    for inst in self._iter_instances('claia.definitions'):
      try:
        plugin_definitions = inst.get_definitions()
      except Exception as e:
        logger.warning(f"Failed collecting definitions from {inst}: {e}")
        continue
      if not plugin_definitions:
        continue
      for name, definition in plugin_definitions.items():
        if name in all_definitions:
          all_definitions[name] = merge_model_definitions(
            all_definitions[name], definition
          )
        else:
          all_definitions[name] = definition

    logger.debug(f"Collected {len(all_definitions)} model definitions")
    return all_definitions

  def get_available_deployments(self) -> Dict[str, DeploymentInfo]:
    """Get all available deployment methods."""
    self.load_all_plugins()
    all_deployments = self._collect_info_dict('claia.deployments', 'get_deployment_info')
    logger.debug(f"Collected {len(all_deployments)} deployment methods")
    return all_deployments

  def get_deployment_plugin(self, deployment_name: str):
    """Get a specific deployment plugin by name."""
    self.load_all_plugins()
    plugin, _ = self._find_plugin_by_name(
      'claia.deployments', 'get_deployment_info', deployment_name
    )
    return plugin


  # TOOLS
  def get_protocol_by_name(self, name: str):
    """Get a tool protocol plugin by name."""
    self.load_all_plugins()
    return self._find_plugin_by_name('claia.tool_protocols', 'get_protocol_info', name)

  def get_module_by_name(self, name: str):
    """Get a tool module plugin by name."""
    self.load_all_plugins()
    return self._find_plugin_by_name('claia.tool_modules', 'get_module_info', name)

  def get_tool_by_name(self, command_name: str):
    """Find a tool by name across all loaded modules."""
    self.load_all_plugins()

    if '.' in command_name:
      module_name, cmd_name = command_name.split('.', 1)
      for inst in self._iter_instances('claia.tool_modules'):
        info = inst.get_module_info()
        if info and info.name == module_name and hasattr(inst, 'get_module_tools'):
          commands = inst.get_module_tools()
          if cmd_name in commands:
            return inst, commands[cmd_name], info
      return None, None, None

    for inst in self._iter_instances('claia.tool_modules'):
      info = inst.get_module_info()
      if info and hasattr(inst, 'get_module_tools'):
        commands = inst.get_module_tools()
        if command_name in commands:
          return inst, commands[command_name], info
    return None, None, None

  def get_all_commands(self) -> Dict[str, Dict]:
    """Get all available commands in hierarchical format."""
    self.load_all_plugins()
    result = {}

    for inst in self._iter_instances('claia.tool_modules'):
      info = inst.get_module_info()
      if not info or not hasattr(inst, 'get_module_tools'):
        continue

      module_entry = {
        "module_info": info,
        "list_of_tools": []
      }

      commands = inst.get_module_tools()
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
    Register an agent class programmatically.

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

    Programmatically registered agents take priority over entry-point
    agents when the same name is used.
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

    Returns both programmatically registered agents and entry-point
    agents. Programmatically registered agents are listed first,
    giving them priority when multiple agents share the same name.
    """
    self.load_all_plugins()
    agents = []

    # Add programmatically registered agents first (priority)
    agents.extend(self._registered_agents.values())

    programmatic_names = set(self._registered_agents.keys())
    for entry in self._iter_entries('claia.agents'):
      info = entry.info
      if info is None:
        continue
      if info.name in programmatic_names:
        logger.debug(f"Entry-point agent '{info.name}' shadowed by programmatic registration")
        continue
      agents.append(info)
    return agents

  def get_agent_info_by_name(self, agent_name: str) -> Optional[AgentInfo]:
    """Get agent info for a specific agent by name.

    Searches through all available agents (both programmatic and
    entry-point). Programmatically registered agents take priority
    when the same name is used.
    """
    agents = self.get_agents()
    for agent_info in agents:
      if agent_info.name == agent_name:
        return agent_info
    return None
