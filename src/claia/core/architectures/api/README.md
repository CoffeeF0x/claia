# API Architectures

Architectures for hosted LLM APIs.

## What lives here

- `anthropic.py` — Anthropic architecture.
- `openai.py` — OpenAI architecture.
- `openrouter.py` — OpenRouter architecture.
- `tools.py` — shared native tool-calling helpers: JSON Schema from
  `ToolReference`, each provider's `tools` array, follow-up
  message shapes, and `ToolChunk` construction.
- `wire.py` — shared OpenAI-wire utility: SSE parsing and provider
  error formatting, used by all three (and by future
  OpenAI-compatible architectures such as llama.cpp/vllm).

These classes are the architecture plugins: they inherit
`APIArchitecture` (see `claia.core.architectures.base`), which sets
`deployment = "api"` and provides the shared `requests.Session` and
key/header handling, and declare their `ArchitectureInfo` via
`@architecture` / `@architecture.param` (credentials, endpoints, and
generation knobs). The `claia.architectures` entry points target
these classes directly.
