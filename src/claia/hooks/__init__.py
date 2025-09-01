"""
Hook specifications for the unified CLAIA system.

This package defines the plugin interfaces for both models and tools:
- Model hooks: ArchitectureHooks, DeploymentHooks, SolverHooks, DefinitionHooks
- Tool hooks: PatternHooks, ProtocolHooks, CommandModuleHooks
"""

from .architecture import ArchitectureHooks, ArchitectureInfo
from .deployment import DeploymentHooks, DeploymentInfo
from .solver import SolverHooks, SolverInfo, DeploymentParams
from .definition import DefinitionHooks, ModelDefinition
from .pattern import PatternHooks, PatternInfo
from .protocol import ProtocolHooks, ProtocolInfo
from .module import CommandModuleHooks, CommandDefinition, ArgumentDefinition

__all__ = [
  'ArchitectureHooks', 'ArchitectureInfo',
  'DeploymentHooks', 'DeploymentInfo',
  'SolverHooks', 'SolverInfo', 'DeploymentParams',
  'DefinitionHooks', 'ModelDefinition',
  'PatternHooks', 'PatternInfo',
  'ProtocolHooks', 'ProtocolInfo',
  'CommandModuleHooks', 'CommandModuleInfo', 'CommandDefinition', 'ArgumentDefinition'
]
