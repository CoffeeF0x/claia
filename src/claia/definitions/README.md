# Model Definitions

Model metadata and configuration objects used by solvers, deployments, and architectures.

## What lives here

- `openai.py`, `anthropic.py` — definitions for provider-specific models.
- `legacy.py` — helpers/mappings for older model naming schemes.

Definitions typically expose `ModelDefinition` objects via hooks in `hooks.definition` and are
discovered through the `claia.definitions` entry point.

## How definitions fit in

- Describe **canonical model names**, **aliases**, **architectures**, and **deployment methods**.
- Provide metadata used by:
  - solvers (to resolve aliases and capabilities)
  - deployments (to know which backends are valid)
  - architectures (to know how to initialize models).

## When to add/modify a definition

- You’re adding a new model ID or alias.
- You’re changing which deployments/architectures are allowed for an existing model.
