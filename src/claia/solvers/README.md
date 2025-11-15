# Solvers

Solvers decide **which deployment + architecture** to use for a given model name and available plugins.

## What lives here

- `default.py` — `DefaultSolverPlugin`, the catch-all solver that:
  - resolves model aliases to canonical model names using definitions
  - selects a deployment method (optionally honoring a requested method)
  - picks an architecture name from the model’s definition
  - returns a `DeploymentParams` wrapped in a `Result`.

## How solvers fit in

- Solvers are discovered via the `claia.solvers` entry point.
- The `Manager` asks solvers:
  - `can_solve(model_name, deployment_preference, **kwargs) -> bool`
  - `solve_deployment(...) -> Result[DeploymentParams]`.
- The `Registry` and model runner use the chosen `DeploymentParams` to:
  - select a deployment plugin
  - select an architecture plugin
  - construct and execute the actual model call.

## When to add/modify a solver

- You want custom routing logic (e.g., cost-based, latency-based, A/B routing).
- You need different behavior per environment or tenant.
- You want smart handling of aliases, fallbacks, or feature flags.
