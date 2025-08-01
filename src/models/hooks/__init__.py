"""
Hook specifications for the refactored CLAIA models system.

This package defines the plugin interfaces for the new architecture:
- ModelHooks: Model plugin interface
- DeploymentHooks: Deployment method plugin interface
- SolverHooks: Deployment solver plugin interface
"""

from .architecture import ArchitectureHooks
from .deployment import DeploymentHooks, DeploymentInfo
from .solver import SolverHooks, SolverInfo, DeploymentParams
from .definition import DefinitionHooks, ModelDefinition

__all__ = [
  'ArchitectureHooks',
  'DeploymentHooks', 'DeploymentInfo',
  'SolverHooks', 'SolverInfo', 'DeploymentParams',
  'DefinitionHooks', 'ModelDefinition'
]
