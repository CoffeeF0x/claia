# Model Architectures

Architecture adapters that translate model definitions into runnable model stacks.

## What lives here

- `openai.py`, `anthropic.py` — API-backed LLM architectures.
- `transformers_generic.py`, `transformers_gemma3.py` — local transformer-based architectures.
- `dummy.py` — no-op/testing architecture.

Each architecture implements hooks defined in `hooks.architecture` and is discovered via the
`claia.architectures` entry point.

## How architectures fit in

- Model **definitions** describe which architectures are valid for a model.
- A **solver** picks an architecture name and deployment method for the request.
- The **deployment** instantiates the architecture and configures credentials/transport.

## When to add/modify an architecture

- You want to support a new provider or a significantly different invocation pattern.
- You need specialized pre/post-processing that doesn’t belong in definitions or deployments.
