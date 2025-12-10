"""
Hook system for CLAIA plugins.

All plugin info classes (ArchitectureInfo, DeploymentInfo, SolverInfo, PatternInfo,
ProtocolInfo, ToolModuleInfo, AgentInfo) share a consistent interface:
- name: str (identifier)
- title/description: str (display info)
- required_args: Optional[List[str]] (kwargs the plugin needs from settings)

The required_args field enables plugins to declare their configuration needs,
allowing the Manager to filter kwargs and Settings to dynamically add options.
"""

from .architecture import ArchitectureHooks, ArchitectureInfo
from .deployment import DeploymentHooks, DeploymentInfo
from .solver import SolverHooks, SolverInfo, DeploymentParams
from .definition import DefinitionHooks, ModelDefinition
from .pattern import PatternHooks, PatternInfo
from .protocol import ProtocolHooks, ProtocolInfo
from .tool import ToolModuleHooks, ToolModuleInfo, ToolDefinition, ArgumentDefinition
from .agent import AgentHooks, AgentInfo

__all__ = [
  'ArchitectureHooks', 'ArchitectureInfo',
  'DeploymentHooks', 'DeploymentInfo',
  'SolverHooks', 'SolverInfo', 'DeploymentParams',
  'DefinitionHooks', 'ModelDefinition',
  'PatternHooks', 'PatternInfo',
  'ProtocolHooks', 'ProtocolInfo',
  'ToolModuleHooks', 'ToolModuleInfo', 'ToolDefinition', 'ArgumentDefinition',
  'AgentHooks', 'AgentInfo'
]
