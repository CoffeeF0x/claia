# Model Definitions

Model metadata and configuration objects used by deployments and architectures.

## What lives here

- `openai.py`, `anthropic.py`, `openrouter.py` — definitions for provider-specific models.
- `legacy.py` — helpers/mappings for older model naming schemes.
- `model_definition.py` — `ModelDefinition` and `merge_model_definitions`.

Definition providers carry a class-level `info: DefinitionsInfo` (name,
title, description) and expose `ModelDefinition` objects through
`BaseDefinitionProvider.get_definitions()`. They are discovered through
the `claia.definitions` entry point. When two providers contribute the
same model name, `merge_model_definitions` walks the dataclass fields
and unions lists and overlays dicts.

## How definitions fit in

- Describe **canonical model names**, **aliases**, **architectures**, and **deployment methods**.
- Provide metadata used by:
  - the registry resolve step (to resolve aliases and pick a deployment/architecture)
  - deployments (to know which backends are valid)
  - architectures (to know how to initialize models).

## When to add/modify a definition

- You’re adding a new model ID or alias.
- You’re changing which deployments/architectures are allowed for an existing model.
