"""
Conversation-domain models.

Artifacts live under ``claia.core.data.artifacts``. This package keeps
Conversation, Message, MessageSequence, and Prompt — types that are not
IO artifacts.
"""

from ..artifacts import (
  AudioArtifact,
  BaseArtifact,
  FileArtifact,
  ImageArtifact,
  LinkArtifact,
  RawArtifact,
  TextArtifact,
)
from .prompt import Prompt
from .conversation import (
  Conversation,
  Message,
  MessageSequence,
  MessageSequenceOrdered,
)

__all__ = [
  "BaseArtifact",
  "TextArtifact",
  "ImageArtifact",
  "AudioArtifact",
  "FileArtifact",
  "LinkArtifact",
  "RawArtifact",
  "Prompt",
  "Conversation",
  "Message",
  "MessageSequence",
  "MessageSequenceOrdered",
]
