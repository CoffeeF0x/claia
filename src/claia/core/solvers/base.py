"""
Abstract base class for solver plugins.

A solver picks a deployment-method and concrete model identifier given a
requested model name and the set of available deployments and definitions.
The framework's ``claia_solvers`` hookspec mirrors this ABC.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..results import Result
from ..plugins.base import SolverInfo


class BaseSolver(ABC):
  """Contract for solver plugins."""

  @abstractmethod
  def get_solver_info(self) -> SolverInfo:
    """Return metadata describing this solver."""

  @abstractmethod
  def can_solve(
    self,
    model_name: str,
    deployment_preference: Optional[str] = None,
    **kwargs,
  ) -> bool:
    """Return True if this solver can resolve a deployment for ``model_name``."""

  @abstractmethod
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
    """
    Resolve a deployment for ``model_name``.

    Returns a ``Result`` containing a ``DeploymentParams`` on success.
    """
