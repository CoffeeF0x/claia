"""Solver pairing and prefetched SolverResult on Registry.run."""

import pytest

from claia.core.data import Conversation
from claia.core.enums.deployment import DeploymentPreference
from claia.core.results import ResolveError
from claia.framework.solver import Solver, SolverResult


def test_solve_alias_returns_pairing(registry_with_fake_manager):
  reg = registry_with_fake_manager
  result = reg.solver.solve("alias1")
  assert isinstance(result, SolverResult)
  assert result.plan.model_name == "dummy"
  assert result.plan.architecture_name == "dummy_arch"
  assert result.plan.deployment_name == "api"
  assert result.definition is not None
  assert result.supports_native_tools is False


def test_solve_unknown_model_raises(registry_with_unknown_model):
  with pytest.raises(ResolveError, match="not found"):
    registry_with_unknown_model.solver.solve("dummy")


def test_solve_rejects_unknown_preference(registry_with_fake_manager):
  with pytest.raises(ResolveError, match="Unknown deployment_preference"):
    registry_with_fake_manager.solver.solve("dummy", "orbit")


def test_solve_local_only_excludes_api(registry_with_fake_manager):
  with pytest.raises(ResolveError, match="api deployment excluded"):
    registry_with_fake_manager.solver.solve(
      "dummy", DeploymentPreference.LOCAL_ONLY,
    )


def test_coerce_preference_accepts_enum_and_string():
  assert Solver.coerce_preference(None) is DeploymentPreference.ANY
  assert Solver.coerce_preference("any") is DeploymentPreference.ANY
  assert (
    Solver.coerce_preference(DeploymentPreference.REMOTE)
    is DeploymentPreference.REMOTE
  )
  assert Solver.coerce_preference("local-only") is DeploymentPreference.LOCAL_ONLY
  with pytest.raises(ResolveError, match="Unknown deployment_preference"):
    Solver.coerce_preference("orbit")


def test_run_with_prefetched_solution_skips_second_solve(registry_with_fake_manager):
  reg = registry_with_fake_manager
  original = reg.solver
  calls = {"n": 0}

  class _CountingSolver(Solver):
    def solve(self, model_name, deployment_preference=DeploymentPreference.ANY):
      calls["n"] += 1
      return original.solve(model_name, deployment_preference)

  reg.solver = _CountingSolver(reg.manager)
  solution = reg.solver.solve("dummy")
  assert calls["n"] == 1

  result = reg.run("dummy", Conversation(title="T"), solution=solution)
  assert result.is_success()
  assert calls["n"] == 1

  result = reg.run("dummy", Conversation(title="T"))
  assert result.is_success()
  assert calls["n"] == 2
