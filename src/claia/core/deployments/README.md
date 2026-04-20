# Deployments

Runtime backends that define **how and where** models run.

## What lives here

- `api.py` — API-based execution (e.g., HTTP clients).
- `local.py` — local runtime (e.g., on-device or server-hosted models).
- `remote.py` — remote runtime (e.g., worker/service backends).
- `dummy.py` — no-op/testing backend.

Each deployment plugin exposes a `DeploymentInfo` and is discovered via the
`claia.deployments` entry point.

## How deployments fit in

- A solver chooses a `deployment_name` and `architecture_name`.
- The deployment:
  - validates/filters kwargs against its declared `ParamSpec` list
  - instantiates the architecture or client
  - executes the request and returns a result.

## When to add/modify a deployment

- You want to support a new execution environment (e.g., different cluster, queue, or API host).
- You need different credentials or transport behavior separated from model logic.
