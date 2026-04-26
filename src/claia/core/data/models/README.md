# Data Models

Pure Python models for CLAIA artifacts and conversations. These classes serialize to dictionaries and keep persistence out of the core library.

## What Lives Here

- `base.py` — `BaseArtifact`, shared identity, metadata, source reference, timestamps, and content cache behavior.
- `text.py` — `TextArtifact`, UTF-8 text content and text media type helpers.
- `image.py` — `ImageArtifact`, image metadata and PIL-compatible content handling.
- `audio.py` — `AudioArtifact`, audio metadata and byte content handling.
- `prompt.py` — `Prompt`, validated prompt names and prompt metadata.
- `conversation/` — `Conversation` and `Message`, including branching threads and domain events.

## How It Fits

Model classes should stay framework-free and storage-free. Add serialization fields through `to_dict()` and `from_dict()`, and let runtimes such as `claia.cli.storage.JsonStore` decide where serialized payloads go.

Use `claia.core.data` for the public import path:

```python
from claia.core.data import Conversation, TextArtifact
```
