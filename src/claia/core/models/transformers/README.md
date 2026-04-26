# Transformer Models

Local transformer model wrappers.

## What lives here

- `generic.py` — generic Hugging Face-style wrapper.
- `gemma3.py` — example specialized adapter.
- `diffusers.py` — generic Diffusers-backed image generation pipeline.

These models typically:
- wrap a local/hosted transformer model
- implement the base model interfaces from `claia.core.models.base`
- may expose INIT `ParamSpec`s (e.g., model path, device) for safe configuration.

## Stable Diffusion 2 Smoke Test

Stable Diffusion 2 is wired through the `diffusers` architecture and the
`local` deployment. It requires the local model extras:

```bash
pip install -e '.[local]'
```

Then run it through the registry and inspect the typed chunks:

```python
from claia.core.data import Conversation
from claia.core.enums.conversation import MessageRole
from claia.core.modality import ChunkKind
from claia.framework.registry import Registry

conversation = Conversation(title="SD2 smoke")
conversation.add_message(MessageRole.USER, "A small fox reading in a library")

registry = Registry()
for chunk in registry.run(
    "stable-diffusion-v2",
    conversation,
    streaming=True,
    device="cuda",
    num_inference_steps=20,
    seed=123,
):
    if chunk.kind is ChunkKind.TEXT:
        print(chunk.data)
    elif chunk.kind is ChunkKind.IMAGE_BYTES:
        print(chunk.metadata)
        with open("sd2-smoke.png", "wb") as f:
            f.write(chunk.data)
```

Use `device="cpu"` for compatibility, though generation will be slow.
