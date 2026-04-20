# API Models

Clients/adapters for hosted LLM APIs.

## What lives here

- `anthropic.py` — Anthropic client/adapter.
- `openai.py` — OpenAI client/adapter.
- `openrouter.py` — OpenRouter client/adapter.

These classes typically:
- inherit from base API model types (see `lib/model/base/`)
- declare INIT-scoped `ParamSpec` entries (e.g., API keys, base URLs) so the `Registry` only passes the kwargs they need.
