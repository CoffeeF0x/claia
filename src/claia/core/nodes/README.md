# Nodes

Places compute lives. A node hosts deployments: given a resolved
pairing from the solver it reuses or provisions a deployed
architecture instance, then streams the generate contract back
(chunks up, `ModelResponse` terminal, wrapped in a `GenerateStream`).

## What lives here

- `base.py` — `BaseNode`: the hosting contract plus the shared
  instance-lifecycle surface (`loaded` / `unload` / `stats`) and the
  `remote` class attribute the solver's `deployment_preference`
  filter reads.
- `local.py` — `LocalNode`, the in-process host (no connection to
  manage; the base behavior is the whole job).

Each node class exposes a class-level `info: NodeInfo` and is
discovered via the `claia.nodes` entry point. Nodes are instantiated
at plugin load; the registry's `get_loaded_models` / `unload_model` /
`get_cache_stats` facades aggregate across them.

Remote nodes (runpod, massedcompute, ...) implement the same
contract over a wire: artifacts across, chunks back, a terminal
frame that becomes the `ModelResponse`. Provisioning primitives
(upload, exec, ports) are internals of specific node modules, not
part of the contract.
