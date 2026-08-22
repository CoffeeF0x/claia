# Deployments

Runtime backends that define **how and where** models run.

## What lives here

- `api.py` — API-based execution (e.g., HTTP clients).
- `local.py` — local runtime (e.g., on-device or server-hosted models).
- `remote.py` — remote runtime (e.g., worker/service backends).
- `dummy.py` — no-op/testing backend.

Each deployment class exposes a class-level `info: DeploymentInfo` and is
discovered via the `claia.deployments` entry point.

## How deployments fit in

- The registry resolve step chooses a `deployment_name` and `architecture_name`, then translates the conversation into a sequence or artifact list.
- The deployment:
  - instantiates the architecture or client
  - runs `model.generate` on those inputs
  - streams chunks back

Deployments do not take a `Conversation`.

## When to add/modify a deployment

- You want to support a new execution environment (e.g., different cluster, queue, or API host).
- You need different credentials or transport behavior separated from model logic.
