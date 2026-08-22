"""
claia.core — the CLAIA library.

Pure data models, plugin contracts (ABCs), and concrete implementations of
architectures, deployments, nodes, definitions, and tools.

``claia.core`` can be imported and used directly without starting the
framework runtime. Applications that want plugin discovery, task
orchestration, and agent lifecycle should use ``claia.framework`` on top.

``claia`` itself is an implicit (PEP 420) namespace package — there is no
top-level ``claia/__init__.py``. Each layer (``claia.core``,
``claia.framework``, ``claia.cli``) is independently installable.
"""

from .results import Result, DeploymentError, ResolveError
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
  GenerateStream,
  Prompt,
  Conversation,
  Message,
  DomainEvent,
)
from .plugins.base import (
  ExtensionInfo,
  ArchitectureInfo,
  DeploymentInfo,
  NodeInfo,
  ProtocolInfo,
  ToolModuleInfo,
  DefinitionsInfo,
  ToolDefinition,
  ArgumentDefinition,
  ToolReference,
  ServingPlan,
  ParamSpec,
)
from .definitions.model_definition import ModelDefinition
from .enums.events import EventType
from .enums.plugins import ParamScope, ParamCategory
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
  "Result", "DeploymentError", "ResolveError",
  # Data
  "DataObject",
  "BaseArtifact", "TextArtifact", "ImageArtifact", "AudioArtifact",
  "FileArtifact", "LinkArtifact", "RawArtifact",
  "BaseChunk", "TextChunk", "ImageChunk", "AudioChunk", "RawChunk",
  "ModelResponse", "GenerateStream",
  "Prompt", "Conversation", "Message",
  "DomainEvent", "EventType",
  # Plugin metadata + contracts
  "ExtensionInfo",
  "ArchitectureInfo", "DeploymentInfo", "NodeInfo",
  "ProtocolInfo", "ToolModuleInfo", "DefinitionsInfo",
  "ToolDefinition", "ArgumentDefinition", "ToolReference", "ServingPlan",
  "ParamSpec", "ParamScope", "ParamCategory",
  "ModelDefinition",
  # Media enums
  "MediaType", "TextFormat", "ImageFormat", "AudioFormat",
  "VideoFormat", "ApplicationFormat",
]
