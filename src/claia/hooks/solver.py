"""
Pluggy hookspecs for solver plugins.

These specs mirror ``BaseSolver`` in ``claia_core.solvers.base``.
"""

import pluggy
from typing import Any, Dict, List, Optional

from claia_core.results import Result
from claia_core.plugins.base import SolverInfo, DeploymentParams


hookspec = pluggy.HookspecMarker("claia_solvers")


class SolverHooks:
  """Hook specifications for solver plugins."""

  @hookspec
  def get_solver_info(self) -> SolverInfo:
    """Return metadata describing this solver."""

  @hookspec
  def can_solve(
    self,
    model_name: str,
    deployment_preference: Optional[str] = None,
    **kwargs,
  ) -> bool:
    """Return True if this solver can resolve a deployment for ``model_name``."""

  @hookspec
  def solve_deployment(
    self,
    model_name: str,
    available_deployments: List[str],
    available_models: Dict[str, Any],
    cache: Dict[str, Any],
    deployment_preference: Optional[str] = None,
    deployment_method: Optional[str] = None,
    **kwargs,
  ) -> Result:
    """Resolve a deployment for ``model_name`` and return ``Result[DeploymentParams]``."""


__all__ = ["SolverHooks", "SolverInfo", "DeploymentParams"]
