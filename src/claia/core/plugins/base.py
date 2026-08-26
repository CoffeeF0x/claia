"""
Plugin metadata dataclasses.

All plugin types share a common ``ExtensionInfo`` base. Per-plugin-type
subclasses add fields specific to that plugin kind. These dataclasses are
pure data (no IoC) and live in ``claia.core`` so that plugin
implementations can construct them without depending on the framework.

Parameters consumed by a plugin are declared as ``ParamSpec`` objects in
``ExtensionInfo.params``. Each spec declares its scope:

- ``ParamScope.INIT`` — passed at plugin construction (credentials,
  static configuration). The framework filters kwargs against these
  specs when instantiating the plugin.
- ``ParamScope.RUNTIME`` — passed per call (generation parameters like
  temperature, max_tokens). Models consume these during ``generate``.

``ParamSpec`` is a strict superset of the information CLI ``Settings``
needs to build command-line flags, env-var lookups, and defaults, so the
same declarations power both plugin-construction-time filtering and
interactive configuration.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from ..enums.plugins import ParamScope, ParamCategory


########################################################################
#                             PARAM SPEC                               #
########################################################################
@dataclass
class ParamSpec:
  """
  Declarative description of a single parameter consumed by a plugin.

  ``ParamSpec`` unifies what plugins need to advertise about their
  configuration. The framework uses these specs to filter kwargs at
  plugin construction (``INIT``) and per-call dispatch (``RUNTIME``).
  The CLI uses them to build arg parsers, env-var readers, validation,
  and masked display.

  Fields:
    - ``name``: the parameter's canonical snake_case name.
    - ``type``: expected Python type (``str`` by default).
    - ``scope``: when the param is consumed (``INIT`` vs ``RUNTIME``).
    - ``required``: whether the plugin treats absence as an error.
    - ``default``: default value when unset.
    - ``description``: human-readable help text.
    - ``choices``: optional finite allowed values (validated by the CLI
      and usable for tab-completion / enumerated help).
    - ``secret``: True for tokens/passwords; CLI masks the value in
      output and Settings warns at discovery time.
    - ``externally_settable``: False for in-code-only parameters that
      should not be exposed via CLI flags, env vars, or settings.json.
      Defaults to True (most params are user-configurable).
    - ``category``: optional ``ParamCategory`` grouping hint for
      hosts that present params. Unset => MISC.
  """
  name: str
  type: type = str
  scope: ParamScope = ParamScope.RUNTIME
  required: bool = False
  default: Any = None
  description: str = ""
  choices: Optional[List[Any]] = None
  secret: bool = False
  externally_settable: bool = True
  category: Optional[ParamCategory] = None


########################################################################
#                    COMMON RUNTIME PARAM CONSTANTS                    #
########################################################################
# Sensible defaults that apply to most chat-style text models.
# Architectures spread this list into their ``ArchitectureInfo.params``
# alongside architecture-specific INIT specs. Per-architecture tweaks
# (e.g. a higher ``max_tokens`` default) are expressed by declaring an
# overriding ``ParamSpec`` with the same ``name`` *before* the spread;
# ``ExtensionInfo.param`` / Registry kwarg resolution use first-match-
# wins, so the override takes precedence while the rest of the list is
# inherited unchanged.
COMMON_TEXT_RUNTIME_PARAMS: List[ParamSpec] = [
  ParamSpec(name="max_tokens", type=int, scope=ParamScope.RUNTIME, default=1000,
            category=ParamCategory.GENERATION,
            description="Maximum number of tokens to generate."),
  ParamSpec(name="temperature", type=float, scope=ParamScope.RUNTIME, default=0.7,
            category=ParamCategory.GENERATION,
            description="Sampling temperature; higher values produce more varied output."),
  ParamSpec(name="top_p", type=float, scope=ParamScope.RUNTIME, default=1.0,
            category=ParamCategory.GENERATION,
            description="Nucleus sampling probability mass."),
  ParamSpec(name="top_k", type=int, scope=ParamScope.RUNTIME, default=None,
            category=ParamCategory.GENERATION,
            description="Restrict sampling to the top-k tokens."),
  ParamSpec(name="n", type=int, scope=ParamScope.RUNTIME, default=1,
            category=ParamCategory.GENERATION,
            description="Number of completions to request per call."),
  ParamSpec(name="stop", type=list, scope=ParamScope.RUNTIME, default=None,
            category=ParamCategory.GENERATION,
            description="Sequence(s) at which generation should stop."),
  ParamSpec(name="stream", type=bool, scope=ParamScope.RUNTIME, default=True,
            category=ParamCategory.GENERATION,
            description="Whether the model should stream partial output."),
]


########################################################################
#                       BASE EXTENSION METADATA                        #
########################################################################
@dataclass
class ExtensionInfo:
  """
  Base information class for all CLAIA extension plugins.

  Provides a consistent interface across all plugin types
  (Architectures, Deployments, Nodes, Definitions, Protocols,
  Tool Modules, Agents):

  - ``name``: unique identifier used for lookups.
  - ``title``: human-readable display name.
  - ``description``: what the extension does.
  - ``params``: ``ParamSpec`` declarations the extension consumes.
    The framework filters kwargs against these specs when constructing
    the object the extension runs — e.g. a model instance — (INIT-scoped)
    and at per-call dispatch (RUNTIME-scoped).
  """
  name: str
  title: str
  description: str
  params: List[ParamSpec] = field(default_factory=list)

  def init_params(self) -> List[ParamSpec]:
    """Return only INIT-scoped parameter specs."""
    return [p for p in self.params if p.scope == ParamScope.INIT]

  def runtime_params(self) -> List[ParamSpec]:
    """Return only RUNTIME-scoped parameter specs."""
    return [p for p in self.params if p.scope == ParamScope.RUNTIME]

  def param(self, name: str) -> Optional[ParamSpec]:
    """Return the ``ParamSpec`` with the given name, or ``None``."""
    for p in self.params:
      if p.name == name:
        return p
    return None


########################################################################
#                       PER-PLUGIN INFO TYPES                          #
########################################################################
@dataclass
class ArchitectureInfo(ExtensionInfo):
  """Information about a model architecture."""
  pass


@dataclass
class DeploymentInfo(ExtensionInfo):
  """Information about a deployment plugin."""
  pass


@dataclass
class NodeInfo(ExtensionInfo):
  """Information about a node plugin."""
  pass


@dataclass
class ProtocolInfo(ExtensionInfo):
  """Information about a tool-protocol plugin."""
  pass


@dataclass
class ToolModuleInfo(ExtensionInfo):
  """Information about a tool-module plugin."""
  pass


@dataclass
class DefinitionsInfo(ExtensionInfo):
  """Information about a model-definition provider."""
  pass


########################################################################
#                       SUPPORTING DATACLASSES                         #
########################################################################
@dataclass
class ArgumentDefinition:
  """Definition of a single argument exposed by a tool."""
  name: str
  description: str
  data_type: str  # 'str' | 'int' | 'float' | 'bool' | 'custom'
  required: bool = False
  default_value: Optional[Any] = None


@dataclass
class ToolDefinition:
  """
  Definition of a tool exposed by a tool-module plugin.

  The ``callable`` must return either:
    - A ``Result`` object (from ``claia.core.results``) — used as-is.
    - A ``str`` — wrapped in ``Result.ok(data=string)``.

  Any other return type is treated as an error by the registry.
  """
  name: str
  description: str
  callable: Callable
  arguments: Dict[str, ArgumentDefinition]


@dataclass
class ToolReference:
  """Protocol-agnostic descriptor of an executable tool.

  Produced by each protocol's ``get_tool_references()`` and stored in
  the registry's unified tool index. The registry uses ``qualified_name``
  to identify the tool and ``protocol_name`` to dispatch execution back
  to the owning protocol. ``parameter_schema`` is intentionally opaque
  to the registry — its shape is protocol-specific (e.g. a
  ``Dict[str, ArgumentDefinition]`` for the simple protocol, a raw JSON
  Schema dict for MCP, etc.). Callers that need to introspect arguments
  (UIs, renderers) must dispatch on the owning protocol.

  See the ExoFox docs repo `claia/overview.md` Decisions for the full rationale.

  Fields:
    - ``qualified_name``: fully-namespaced tool name, e.g.
      ``"system.exit"`` for native modules or
      ``"mcp.<server>.<tool>"`` for MCP-sourced tools.
    - ``description``: human-readable description surfaced by UIs and
      help text. Sourced from the protocol's own metadata.
    - ``protocol_name``: name of the protocol that owns and runs this
      tool. The registry uses this to route ``execute_tool`` calls.
    - ``parameter_schema``: protocol-specific description of the tool's
      parameters. Opaque to the registry.
    - ``tags``: optional free-form tags for UI filtering / grouping.
  """
  qualified_name: str
  description: str
  protocol_name: str
  parameter_schema: Any = None
  tags: List[str] = field(default_factory=list)


@dataclass
class ServingPlan:
  """Solver output: the resolved serving pairing for one model call.

  ``provider_model_name`` is the identifier handed to the architecture
  (from the definition's ``identifiers`` map when present, otherwise
  the canonical name).
  """
  model_name: str
  provider_model_name: str
  architecture_name: str
  deployment_name: str
  node_name: str
