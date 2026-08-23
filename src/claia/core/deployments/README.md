# Deployments

The serving layer: a deployment turns an architecture class into a
servable instance and manages the stream between that instance and
the hosting node.

## What lives here

- `base.py` — `BaseDeployment`: `deploy` / `teardown` / `run` (the
  relay + metering path) and the `api` class attribute the solver's
  `DeploymentPreference` filter reads.
- `api.py` — session factory + metering relay for hosted-API
  architectures.
- `transformers.py` — in-process weight loading and release for
  local architectures.
- `dummy.py` — no-op/testing deployment.

Each deployment class exposes a class-level `info: DeploymentInfo`
and is discovered via the `claia.deployments` entry point.

## How deployments fit in

- The solver picks the pairing (architecture → its declared
  deployment → an allowed node) and the registry translates the
  conversation into a sequence or artifact list.
- The node asks the deployment to `deploy(architecture_class,
  model_name, init_kwargs)` — or reuses a cached instance — then
  calls `run(instance, inputs, runtime_kwargs)`.
- `run` returns an `AgentResponse`: relays the architecture's
  chunks unchanged, yields a `MetricsChunk` after the stream
  finishes, and marks `complete` / `error` on mid-stream failure.

Deployments do not take a `Conversation`.

## When to add/modify a deployment

- You want to serve architectures with a new tool (llama.cpp, vllm,
  a custom runtime).
- You need different transport or lifecycle behavior separated from
  inference logic.
