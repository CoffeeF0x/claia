"""
Hook system for CLAIA agent plugins.
"""

from .architecture import ArchitectureHooks, ArchitectureInfo
from .deployment import DeploymentHooks, DeploymentInfo
from .solver import SolverHooks, SolverInfo, DeploymentParams
from .definition import DefinitionHooks, ModelDefinition
from .pattern import PatternHooks, PatternInfo
from .protocol import ProtocolHooks, ProtocolInfo
from .module import CommandModuleHooks, CommandDefinition, ArgumentDefinition
from .agent import AgentHooks, AgentInfo

__all__ = [
  'ArchitectureHooks', 'ArchitectureInfo',
  'DeploymentHooks', 'DeploymentInfo',
  'SolverHooks', 'SolverInfo', 'DeploymentParams',
  'DefinitionHooks', 'ModelDefinition',
  'PatternHooks', 'PatternInfo',
  'ProtocolHooks', 'ProtocolInfo',
  'CommandModuleHooks', 'CommandDefinition', 'ArgumentDefinition',
  'AgentHooks', 'AgentInfo'
]
