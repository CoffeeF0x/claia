# API Models

Clients/adapters for hosted LLM APIs.

## What lives here

- `anthropic.py` — Anthropic client/adapter.
- `openai.py` — OpenAI client/adapter.
- `openrouter.py` — OpenRouter client/adapter.

These classes are the architecture plugins: they inherit from base API
model types (see `claia.core.models.base`) and declare their
`ArchitectureInfo` via `@architecture` / `@architecture.param`
(credentials, endpoints, and generation knobs). The `claia.architectures`
entry points target these classes directly.
