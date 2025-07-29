"""
Hook specifications for the refactored CLAIA models system.

This package defines the plugin interfaces for the new architecture:
- ModelHooks: Model plugin interface
- DeploymentHooks: Deployment method plugin interface
- SolverHooks: Deployment solver plugin interface
"""

from .architecture_hooks import ArchitectureHooks, ArchitectureInfo
from .deployment_hooks import DeploymentHooks, DeploymentInfo
from .solver_hooks import SolverHooks, SolverInfo, DeploymentParams
from .definition_hooks import DefinitionHooks, ModelDefinition

__all__ = [
  'ArchitectureHooks', 'ArchitectureInfo',
  'DeploymentHooks', 'DeploymentInfo',
  'SolverHooks', 'SolverInfo', 'DeploymentParams',
  'DefinitionHooks', 'ModelDefinition'
]
