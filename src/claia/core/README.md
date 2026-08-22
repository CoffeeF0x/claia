# Core

`claia.core` is the library layer: data models, result types, plugin contracts, and the built-in serving stack and tools. Its public contracts stay framework-free so they can be used without starting the registry runtime.

## What Lives Here

- `data/` — artifacts, prompts, conversations, messages, domain events, and utilities.
- `plugins/` — shared metadata dataclasses such as `ParamSpec`, `ArchitectureInfo`, `ToolDefinition`, and `ServingPlan`.
- `architectures/` — the inference layer: concrete API, transformer, dummy, and base classes. Architecture entry points target these classes directly.
- `deployments/` — api, transformers, and dummy deployments (serve an architecture, relay + meter the stream).
- `nodes/` — places compute lives; hosting and instance lifecycle.
- `definitions/` — canonical model IDs, provider metadata, and definition merging.
- `tools/` — tool modules and execution protocols.
- `enums/` and `results.py` — shared value types used across the layers.

## How It Fits

Core code is intentionally importable on its own. Plugin implementations can subclass core ABCs and return core metadata without importing `claia.framework`. The framework layer discovers those implementations via entry points and exposes them through `Registry`.

Use `claia.core` directly when you are implementing or testing an architecture, deployment, node, definition, tool, or data model. Use `claia.framework` when you need discovery, orchestration, workers, or app-facing convenience imports.
