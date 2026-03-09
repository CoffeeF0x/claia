"""
Media package for CLAIA.

Provides pure data models for managing CLAIA domain objects (text, images,
audio, prompts, conversations). Models are independent of persistence.

Main exports:
    Models:
        - BaseArtifact: Base artifact model
        - TextArtifact: Text artifact model
        - ImageArtifact: Image artifact model
        - AudioArtifact: Audio artifact model
        - Prompt: Prompt template model
        - Conversation: Conversation model
        - Message: Conversation message model
        - Action: Conversation action/audit model
        - ConversationSettings: Conversation settings

    Utils:
        - utils.image: Image processing utilities (base64, resize, convert, etc.)
        - utils.text: Text processing utilities (encoding, normalization, etc.)
"""

# Export models
from .models import (
    BaseArtifact,
    TextArtifact,
    ImageArtifact,
    AudioArtifact,
    Prompt,
    Conversation,
    Message,
    Action,
    ConversationSettings,
)

# Export events
from .events import DomainEvent

# Export utils module
from . import utils

__all__ = [
    # Models
    "BaseArtifact",
    "TextArtifact",
    "ImageArtifact",
    "AudioArtifact",
    "Prompt",
    "Conversation",
    "Message",
    "Action",
    "ConversationSettings",
    # Events
    "DomainEvent",
    # Utils
    "utils",
]

