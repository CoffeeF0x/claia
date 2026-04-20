"""
Media package for CLAIA.

Provides pure data models for managing CLAIA domain objects (text, images,
audio, prompts, conversations). Models are independent of persistence.
"""

from .models import (
    BaseArtifact,
    TextArtifact,
    ImageArtifact,
    AudioArtifact,
    Prompt,
    Conversation,
    Message,
)

from .events import DomainEvent, EventType

from . import utils

__all__ = [
    "BaseArtifact",
    "TextArtifact",
    "ImageArtifact",
    "AudioArtifact",
    "Prompt",
    "Conversation",
    "Message",
    "DomainEvent",
    "EventType",
    "utils",
]
