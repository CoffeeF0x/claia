"""
Hook specifications for deployment solver plugins.

Solver plugins determine which deployment method and model to use
based on user preferences, model availability, and system constraints.
"""

import pluggy
from typing import Optional, Dict, List, Any
from dataclasses import dataclass

# Internal dependencies
from claia.lib.results import Result


@dataclass
class SolverInfo:
  """Information about a deployment solver provided by a solver plugin."""
  name: str
  title: str
  description: str
  settings: Optional[Dict[str, Any]] = None
  required_args: Optional[List[str]] = None  # list of custom args required by the solver


@dataclass
class DeploymentParams:
  """Simplified deployment parameters returned by solver."""
  deployment_name: str
  model_name: str
  architecture_name: str


# Create hookspec decorator
hookspec = pluggy.HookspecMarker("claia_solvers")


class SolverHooks:
  """Hook specifications for deployment solver plugins."""

  @hookspec
  def get_solver_info(self) -> SolverInfo:
    """
    Get information about this solver.

    Returns:
        SolverInfo object describing this solver
    """

  @hookspec
  def can_solve(self, model_name: str, deployment_preference: Optional[str] = None, **kwargs) -> bool:
    """
    Check if this solver can handle the given model and preferences.

    Args:
        model_name: Canonical model name
        deployment_preference: Optional deployment preference string
        **kwargs: Additional parameters

    Returns:
        True if this solver can handle the request
    """

  @hookspec
  def solve_deployment(
    self,
    model_name: str,
    available_deployments: List[str],
    available_models: Dict[str, Any],
    cache: Dict[str, Any],
    deployment_preference: Optional[str] = None,
    deployment_method: Optional[str] = None,
    **kwargs
  ) -> Result:
    """
    Determine the best deployment method and model for the request.

    Args:
        model_name: Raw model name (may need resolution)
        available_deployments: List of available deployment method names
        available_models: Dict of available models with their info
        cache: Cache dictionary for model instances
        deployment_preference: Optional deployment preference string
        deployment_method: Optional forced deployment method
        **kwargs: Additional parameters (api keys, device preferences, etc.)

    Returns:
        Result containing DeploymentParams or error
    """
