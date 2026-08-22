# Dummy Architectures

Testing and development stub architectures.

## What lives here

- `dummy.py` — predictable behavior for tests and examples.
  `DummyArchitecture` is also the `dummy` architecture plugin
  (`@architecture.name("dummy")`), served by the `dummy` deployment.

Use these when you want to exercise orchestration logic (nodes,
deployments, agents, tools) without incurring real model costs or
external API calls.
