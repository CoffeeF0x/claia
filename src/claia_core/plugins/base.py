"""
Plugin metadata dataclasses.

All plugin types share a common ``ExtensionInfo`` base. Per-plugin-type
subclasses add fields specific to that plugin kind. These dataclasses are
pure data (no pluggy, no IoC) and live in claia_core so that:

- Plugin implementations can construct them without depending on the
  framework.
- The framework's hookspecs in ``claia.hooks`` can use them as type hints
  and pluggy return types.

The ``required_args`` field allows plugins to declare which settings they
consume, enabling the framework to filter kwargs at plugin construction.

NOTE: ``ParamSpec``-based parameter declarations are planned for Phase 3
of the migration and will eventually replace the loose ``required_args``
list. See ``docs/integration-plan.md``.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


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
  - ``required_args``: settings the extension consumes from the host
    application's settings. The framework uses this to filter ``kwargs``
    passed to plugin constructors.
  """
  name: str
  title: str
  description: str
  required_args: Optional[List[str]] = None


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
    - A ``Result`` object (from ``claia_core.results``) — used as-is.
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
