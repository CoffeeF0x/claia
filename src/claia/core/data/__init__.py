"""
Data package for CLAIA.

Provides pure data models for IO (artifacts / chunks / AgentRequest /
AgentResponse) and conversation-domain objects. Models are independent
of persistence.
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
  ToolChunk,
  UsageChunk,
  MetricsChunk,
)
from .request import AgentRequest, ModelInputs
from .response import AgentResponse
from .models import (
  Prompt,
  Conversation,
  Message,
  MessageSequence,
  MessageSequenceOrdered,
)
from .events import DomainEvent
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
  "ToolChunk",
  "UsageChunk",
  "MetricsChunk",
  "AgentRequest",
  "ModelInputs",
  "AgentResponse",
  "Prompt",
  "Conversation",
  "Message",
  "MessageSequence",
  "MessageSequenceOrdered",
  "DomainEvent",
  "utils",
]
