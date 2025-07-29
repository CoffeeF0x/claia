"""
Hook specifications for the refactored CLAIA models system.

This package defines the plugin interfaces for the new architecture:
- ModelHooks: Model plugin interface
- DeploymentHooks: Deployment method plugin interface
- SolverHooks: Deployment solver plugin interface
"""

from .model_hooks import ModelHooks, ModelInfo
from .deployment_hooks import DeploymentHooks, DeploymentInfo
from .solver_hooks import SolverHooks, SolverInfo, DeploymentParams

__all__ = [
  'ModelHooks', 'ModelInfo',
  'DeploymentHooks', 'DeploymentInfo',
  'SolverHooks', 'SolverInfo', 'DeploymentParams'
]
