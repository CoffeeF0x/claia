"""
Data package for CLAIA.

Provides pure data models for IO (artifacts / chunks / ModelResponse) and
conversation-domain objects. Models are independent of persistence.
"""

from .common import DataObject
from .artifacts import (
  BaseArtifact,
  TextArtifact,
  ImageArtifact,
  AudioArtifact,
  FileArtifact,
  LinkArtifact,
  RawArtifact,
  ToolArtifact,
)
from .chunks import (
  BaseChunk,
  TextChunk,
  ImageChunk,
  AudioChunk,
  RawChunk,
)
from .response import ModelResponse
from .models import (
  Prompt,
  Conversation,
  Message,
  MessageSequence,
  MessageSequenceOrdered,
)
from .events import DomainEvent, EventType
from . import utils

__all__ = [
  "DataObject",
  "BaseArtifact",
  "TextArtifact",
  "ImageArtifact",
  "AudioArtifact",
  "FileArtifact",
  "LinkArtifact",
  "RawArtifact",
  "ToolArtifact",
  "BaseChunk",
  "TextChunk",
  "ImageChunk",
  "AudioChunk",
  "RawChunk",
  "ModelResponse",
  "Prompt",
  "Conversation",
  "Message",
  "MessageSequence",
  "MessageSequenceOrdered",
  "DomainEvent",
  "EventType",
  "utils",
]
