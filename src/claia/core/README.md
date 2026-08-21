# Core

`claia.core` is the library layer: data models, result types, plugin contracts, and built-in model/tool implementations. Its public contracts stay framework-free so they can be used without starting the registry runtime.

## What Lives Here

- `data/` — artifacts, prompts, conversations, messages, domain events, and utilities.
- `plugins/` — shared metadata dataclasses such as `ParamSpec`, `ArchitectureInfo`, `ToolDefinition`, and `DeploymentParams`.
- `deployments/` — API, local, remote, and dummy execution backends.
- `definitions/` — canonical model IDs, provider metadata, and definition merging.
- `models/` — concrete API, transformer, dummy, and base model classes. Architecture entry points target these classes directly.
- `tools/` — tool modules and execution protocols.
- `enums/`, `modality.py`, and `results.py` — shared value types used across the layers.

## How It Fits

Core code is intentionally importable on its own. Plugin implementations can subclass core ABCs and return core metadata without importing `claia.framework`. The framework layer discovers those implementations via entry points and exposes them through `Registry`.

Use `claia.core` directly when you are implementing or testing a model, deployment, definition, tool, or data model. Use `claia.framework` when you need discovery, orchestration, workers, or app-facing convenience imports.
