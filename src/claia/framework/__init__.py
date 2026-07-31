"""
claia.framework — the CLAIA orchestration runtime.

Provides the inversion-of-control runtime on top of ``claia.core``:

- ``Manager`` discovers plugins via pluggy entry points (architectures,
  deployments, solvers, definitions, tool protocols/modules, agents).
- ``Registry`` is the application-facing composition root that
  orchestrates models, tools, and agents.
- ``Process`` and ``ProcessQueue`` model units of work; worker threads
  spawned by the registry consume them.
- ``BaseAgent`` and the built-in ``simple`` agent live under
  ``claia.framework.agents``.

Because ``claia`` itself is a namespace package (no top-level
``__init__.py``), this module also serves as the convenience hub:
commonly used types from ``claia.core`` are re-exported here so callers
can do::

    from claia.framework import Registry, Conversation, Result

without having to import from two places.
"""

# Re-exports from claia.core for convenience.
from claia.core.results import Result, DeploymentError
from claia.core.data import (
  Conversation,
  Message,
  DataObject,
  BaseArtifact,
  TextArtifact,
  ImageArtifact,
  AudioArtifact,
  FileArtifact,
  LinkArtifact,
  RawArtifact,
  Prompt,
  BaseChunk,
  TextChunk,
  ImageChunk,
  AudioChunk,
  RawChunk,
  ModelResponse,
  DomainEvent,
  EventType,
)
from claia.core.plugins.base import (
  ExtensionInfo,
  ArchitectureInfo,
  DeploymentInfo,
  SolverInfo,
  ProtocolInfo,
  ToolModuleInfo,
  ToolDefinition,
  ArgumentDefinition,
  ToolReference,
  DeploymentParams,
  ParamSpec,
  ParamScope,
  SettingCategory,
)
from claia.core.definitions.model_definition import ModelDefinition
from claia.core.enums.process_queue import ProcessQueueHook
from claia.core.modality import Modality
from claia.core.enums.data import (
  MediaType,
  TextFormat,
  ImageFormat,
  AudioFormat,
  VideoFormat,
  ApplicationFormat,
)

# Framework primitives.
from .process import Process
from .queue import ProcessQueue
from .registry import Registry
from .manager import Manager
from .agents.base import BaseAgent

__all__ = [
  # Framework primitives
  "Registry", "Manager", "Process", "ProcessQueue", "ProcessQueueHook",
  "BaseAgent",
  # Results
  "Result", "DeploymentError",
  # Data
  "Conversation", "Message",
  "DataObject",
  "BaseArtifact", "TextArtifact", "ImageArtifact", "AudioArtifact",
  "FileArtifact", "LinkArtifact", "RawArtifact", "Prompt",
  "BaseChunk", "TextChunk", "ImageChunk", "AudioChunk", "RawChunk",
  "ModelResponse",
  "DomainEvent", "EventType",
  # Plugin metadata
  "ExtensionInfo",
  "ArchitectureInfo", "DeploymentInfo", "SolverInfo",
  "ProtocolInfo", "ToolModuleInfo",
  "ToolDefinition", "ArgumentDefinition", "ToolReference", "DeploymentParams",
  "ParamSpec", "ParamScope", "SettingCategory",
  "ModelDefinition",
  # Modality / media enums
  "Modality",
  "MediaType", "TextFormat", "ImageFormat", "AudioFormat",
  "VideoFormat", "ApplicationFormat",
]
