"""
claia.core — the CLAIA library.

Pure data models, plugin contracts (ABCs), and concrete implementations of
model architectures, deployments, definitions, and tools.

``claia.core`` can be imported and used directly without starting the
framework runtime. Applications that want plugin discovery, process
orchestration, and agent lifecycle should use ``claia.framework`` on top.

``claia`` itself is an implicit (PEP 420) namespace package — there is no
top-level ``claia/__init__.py``. Each layer (``claia.core``,
``claia.framework``, ``claia.cli``) is independently installable.
"""

from .results import Result, DeploymentError
from .data import (
  DataObject,
  BaseArtifact,
  TextArtifact,
  ImageArtifact,
  AudioArtifact,
  FileArtifact,
  LinkArtifact,
  RawArtifact,
  BaseChunk,
  TextChunk,
  ImageChunk,
  AudioChunk,
  RawChunk,
  ModelResponse,
  Prompt,
  Conversation,
  Message,
  DomainEvent,
  EventType,
)
from .plugins.base import (
  ExtensionInfo,
  ArchitectureInfo,
  DeploymentInfo,
  ProtocolInfo,
  ToolModuleInfo,
  DefinitionsInfo,
  ToolDefinition,
  ArgumentDefinition,
  ToolReference,
  DeploymentParams,
  ParamSpec,
  ParamScope,
  SettingCategory,
)
from .definitions.model_definition import ModelDefinition
from .enums.data import (
  MediaType,
  TextFormat,
  ImageFormat,
  AudioFormat,
  VideoFormat,
  ApplicationFormat,
)

__all__ = [
  # Results
  "Result", "DeploymentError",
  # Data
  "DataObject",
  "BaseArtifact", "TextArtifact", "ImageArtifact", "AudioArtifact",
  "FileArtifact", "LinkArtifact", "RawArtifact",
  "BaseChunk", "TextChunk", "ImageChunk", "AudioChunk", "RawChunk",
  "ModelResponse",
  "Prompt", "Conversation", "Message",
  "DomainEvent", "EventType",
  # Plugin metadata + contracts
  "ExtensionInfo",
  "ArchitectureInfo", "DeploymentInfo",
  "ProtocolInfo", "ToolModuleInfo", "DefinitionsInfo",
  "ToolDefinition", "ArgumentDefinition", "ToolReference", "DeploymentParams",
  "ParamSpec", "ParamScope", "SettingCategory",
  "ModelDefinition",
  # Media enums
  "MediaType", "TextFormat", "ImageFormat", "AudioFormat",
  "VideoFormat", "ApplicationFormat",
]
