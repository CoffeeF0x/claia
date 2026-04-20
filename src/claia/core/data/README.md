## Data/Media Package

Pure data models and repository interfaces for managing media-like data:
text, images, audio, prompts, and conversations.

## What lives here

- `models/`:
  - `base.py` — `BaseFile` (common file metadata + IDs).
  - `text.py`, `image.py`, `audio.py` — `TextFile`, `ImageFile`, `AudioFile`.
  - `prompt.py` — `Prompt` template model.
  - `conversation/` — `Conversation`, `Message`, `Action`.
- `repositories/`:
  - `base.py`, `file_system.py`, `memory.py` — `FileRepository`, `FileSystemRepository`, `MemoryRepository`.
- `utils/` — helpers for text/image/media handling.

## How it fits (TL;DR)

- This package is a **pure data layer**:
  - models know nothing about filesystems or databases
  - repositories handle persistence and storage layout.
- Higher-level code (CLI, registry, agents) works with these models via repository interfaces.

## Quick usage example

```python
from claia.lib.data import TextFile, ImageFile, FileRepository

# Create models
text = TextFile.from_content("Hello, world!", "greeting.txt")
image = ImageFile.from_path("/path/to/photo.jpg", is_reference=False)

# Persist with a repository
repo = FileRepository.create_file_system("/data")
repo.save(text)
repo.save(image)

# Load later
loaded = repo.load(text.id, load_content=True)
print(loaded.content)
```
