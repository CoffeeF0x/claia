"""
Hook system for CLAIA agent plugins.
"""

from .architecture import ArchitectureHooks, ArchitectureInfo
from .deployment import DeploymentHooks, DeploymentInfo
from .solver import SolverHooks, SolverInfo, DeploymentParams
from .definition import DefinitionHooks, ModelDefinition
from .pattern import PatternHooks, PatternInfo
from .protocol import ProtocolHooks, ProtocolInfo
from .tool import ToolModuleHooks, ToolDefinition, ArgumentDefinition
from .agent import AgentHooks, AgentInfo

__all__ = [
  'ArchitectureHooks', 'ArchitectureInfo',
  'DeploymentHooks', 'DeploymentInfo',
  'SolverHooks', 'SolverInfo', 'DeploymentParams',
  'DefinitionHooks', 'ModelDefinition',
  'PatternHooks', 'PatternInfo',
  'ProtocolHooks', 'ProtocolInfo',
  'ToolModuleHooks', 'ToolDefinition', 'ArgumentDefinition',
  'AgentHooks', 'AgentInfo'
]
