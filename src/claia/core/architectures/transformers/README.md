# Transformer Architectures

Local weight-holding architectures.

## What lives here

- `generic.py` — generic Hugging Face-style causal-LM architecture.
- `gemma3.py` — example specialized architecture.
- `diffusers.py` — generic Diffusers-backed image generation pipeline.
- `tts.py` — generic local text-to-speech architecture with backend adapters.

These classes are the architecture plugins: they wrap a local transformer
or Diffusers/TTS backend, inherit `LocalArchitecture` (see
`claia.core.architectures.base`, which sets `deployment = "transformers"`),
and declare their `ArchitectureInfo` via `@architecture` /
`@architecture.param`. `Gemma3Architecture` subclasses
`GenericTransformerArchitecture` and declares only the overrides (name,
title, description, and generation defaults). The `claia.architectures`
entry points target these classes directly.

## Stable Diffusion 2 Smoke Test

Stable Diffusion 2 is wired through the `diffusers` architecture and the
`transformers` deployment. It requires the local model extras:

```bash
pip install -e '.[local]'
```

Then run it through the registry and inspect the typed chunks:

```python
from claia.core.data import Conversation
from claia.core.data.chunks import ImageChunk, TextChunk
from claia.core.enums.conversation import MessageRole
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
    if isinstance(chunk, TextChunk):
        print(chunk.data)
    elif isinstance(chunk, ImageChunk):
        print(chunk.metadata)
        with open("sd2-smoke.png", "wb") as f:
            f.write(chunk.data)
```

Use `device="cpu"` for compatibility, though generation will be slow.

## Qwen3 TTS Smoke Test

Qwen3-TTS 0.6B is wired through the `tts` architecture and the
`transformers` deployment. It requires the audio model extras:

```bash
pip install -e '.[audio]'
```

Then run it through the registry and inspect the typed chunks. The base
checkpoint uses voice cloning, so provide a reference audio path. Claia
passes the request text as the reference text by default:

```python
from claia.core.data import Conversation
from claia.core.data.chunks import AudioChunk, TextChunk
from claia.core.enums.conversation import MessageRole
from claia.framework.registry import Registry

conversation = Conversation(title="Qwen TTS smoke")
conversation.add_message(MessageRole.USER, "Hello from Claia.")

registry = Registry()
for chunk in registry.run(
    "qwen3-tts-0.6b",
    conversation,
    streaming=True,
    device="cuda",
    language="English",
    reference_audio_path="/path/to/reference.wav",
):
    if isinstance(chunk, TextChunk):
        print(chunk.data)
    elif isinstance(chunk, AudioChunk):
        print(chunk.metadata)
        with open("qwen-tts-smoke.wav", "wb") as f:
            f.write(chunk.data)
```
