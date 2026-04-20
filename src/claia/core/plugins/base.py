"""
Plugin metadata dataclasses.

All plugin types share a common ``ExtensionInfo`` base. Per-plugin-type
subclasses add fields specific to that plugin kind. These dataclasses are
pure data (no pluggy, no IoC) and live in ``claia.core`` so that:

- Plugin implementations can construct them without depending on the
  framework.
- The framework's hookspecs in ``claia.framework.hooks`` can use them as
  type hints and pluggy return types.

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
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


########################################################################
#                          SETTING CATEGORIES                          #
########################################################################
class SettingCategory(Enum):
  """Categories for grouping parameters in CLI / settings UIs."""
  API = "API Credentials"
  ENDPOINT = "Endpoints & URLs"
  DIRECTORY = "Directories"
  MODEL = "Model Settings"
  PROMPT = "Prompt Settings"
  AGENT = "Agent Settings"
  VLLM = "VLLM Settings"
  APPLICATION = "Application Settings"
  INTEGRATION = "External Integrations"
  EXTENSION = "Extension Settings"
  GENERATION = "Generation Parameters"
  MISC = "Miscellaneous"


########################################################################
#                             PARAM SPEC                               #
########################################################################
class ParamScope(Enum):
  """When a parameter is consumed relative to the plugin lifecycle."""
  INIT = "init"        # Passed at plugin construction (credentials, config)
  RUNTIME = "runtime"  # Passed per call (generation params, per-request overrides)


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
    - ``category``: grouping hint for settings UIs. Unset => MISC.
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
  category: Optional[SettingCategory] = None


########################################################################
#                       BASE EXTENSION METADATA                        #
########################################################################
@dataclass
class ExtensionInfo:
  """
  Base information class for all CLAIA extension plugins.

  Provides a consistent interface across all plugin types
  (Architectures, Deployments, Solvers, Patterns, Protocols, Tool
  Modules, Agents):

  - ``name``: unique identifier used for lookups.
  - ``title``: human-readable display name.
  - ``description``: what the extension does.
  - ``params``: ``ParamSpec`` declarations the extension consumes.
    The framework filters kwargs against these specs at plugin
    construction (INIT-scoped) and per-call dispatch (RUNTIME-scoped).
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
  """Information about an architecture plugin."""
  pass


@dataclass
class DeploymentInfo(ExtensionInfo):
  """Information about a deployment-method plugin."""
  pass


@dataclass
class SolverInfo(ExtensionInfo):
  """Information about a deployment-solver plugin."""
  settings: Optional[Dict[str, Any]] = field(default=None)


@dataclass
class PatternInfo(ExtensionInfo):
  """Information about a tool-calling pattern plugin."""
  opening_token: str = field(default="")
  closing_token: str = field(default="")
  prompt_template: Optional[str] = field(default=None)


@dataclass
class ProtocolInfo(ExtensionInfo):
  """Information about a tool-protocol plugin."""
  pass


@dataclass
class ToolModuleInfo(ExtensionInfo):
  """Information about a tool-module plugin."""
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
class ToolCallMatch:
  """A single tool-call invocation found in message content by a pattern."""
  start_index: int
  end_index: int  # exclusive, suitable for slice replacement
  tool_name: str
  parameters: Dict[str, Any]
  raw: Optional[str] = None


@dataclass
class DeploymentParams:
  """Resolved deployment parameters returned by a solver."""
  deployment_name: str
  model_name: str
  architecture_name: str
