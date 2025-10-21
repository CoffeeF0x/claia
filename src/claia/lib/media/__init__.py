"""
Media package for CLAIA.

Provides pure data models and repository interfaces for managing media files
(text, images, audio, prompts). Models are independent of persistence, and
repositories provide pluggable storage backends.

Main exports:
    Models:
        - BaseFile: Base file model
        - TextFile: Text file model
        - ImageFile: Image file model
        - AudioFile: Audio file model
        - Prompt: Prompt template model

    Repositories:
        - FileRepository: Abstract base repository
        - FileSystemRepository: File system storage
        - MemoryRepository: In-memory storage
        
    Utils:
        - utils.image: Image processing utilities (base64, resize, convert, etc.)
        - utils.text: Text processing utilities (encoding, normalization, etc.)
"""

# Export models
from .models import (
    BaseFile,
    TextFile,
    ImageFile,
    AudioFile,
    Prompt,
)

# Export repositories
from .repositories import (
    FileRepository,
    FileSystemRepository,
    MemoryRepository,
)

# Export utils module
from . import utils

__all__ = [
    # Models
    "BaseFile",
    "TextFile",
    "ImageFile",
    "AudioFile",
    "Prompt",
    # Repositories
    "FileRepository",
    "FileSystemRepository",
    "MemoryRepository",
    # Utils
    "utils",
]

