# Transformer Models

Local transformer model wrappers.

## What lives here

- `generic.py` — generic Hugging Face-style wrapper.
- `gemma3.py` — example specialized adapter.
- `diffusion.py` — image generation pipeline.

These models typically:
- wrap a local/hosted transformer model
- implement the base model interfaces from `lib/model/base/`
- may expose INIT `ParamSpec`s (e.g., model path, device) for safe configuration.
