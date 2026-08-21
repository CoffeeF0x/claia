# Dummy Models

Testing and development stub models.

## What lives here

- `dummy.py` — predictable behavior for tests and examples. `DummyModel`
  is also the `dummy` architecture plugin (`@architecture.name("dummy")`).

Use these models when you want to exercise orchestration logic (deployments, agents, tools)
without incurring real model costs or external API calls.
