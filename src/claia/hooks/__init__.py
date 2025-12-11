"""
Hook system for CLAIA plugins.

ExtensionInfo is the base class for all plugin info types. It provides a
consistent interface for configuration and discovery:
- name: str (unique identifier)
- title: str (human-readable display name)
- description: str (what the plugin does)
- required_args: Optional[List[str]] (settings the plugin needs)

All info classes extend ExtensionInfo:
- ArchitectureInfo, DeploymentInfo, ProtocolInfo, ToolModuleInfo (no extra fields)
- SolverInfo: adds 'settings' dict
- PatternInfo: adds 'opening_token', 'closing_token', 'prompt_template'
- AgentInfo: adds 'agent_class'

The required_args field enables plugins to declare their configuration needs,
allowing the Manager to filter kwargs and Settings to dynamically add options.
"""

from .base import ExtensionInfo
from .architecture import ArchitectureHooks, ArchitectureInfo
from .deployment import DeploymentHooks, DeploymentInfo
from .solver import SolverHooks, SolverInfo, DeploymentParams
from .definition import DefinitionHooks, ModelDefinition
from .pattern import PatternHooks, PatternInfo
from .protocol import ProtocolHooks, ProtocolInfo
from .tool import ToolModuleHooks, ToolModuleInfo, ToolDefinition, ArgumentDefinition
from .agent import AgentHooks, AgentInfo

__all__ = [
  'ExtensionInfo',
  'ArchitectureHooks', 'ArchitectureInfo',
  'DeploymentHooks', 'DeploymentInfo',
  'SolverHooks', 'SolverInfo', 'DeploymentParams',
  'DefinitionHooks', 'ModelDefinition',
  'PatternHooks', 'PatternInfo',
  'ProtocolHooks', 'ProtocolInfo',
  'ToolModuleHooks', 'ToolModuleInfo', 'ToolDefinition', 'ArgumentDefinition',
  'AgentHooks', 'AgentInfo'
]
