"""
claia.core — the CLAIA library.

Pure data models, plugin contracts (ABCs), and concrete implementations of
model architectures, deployments, solvers, definitions, and tools.

``claia.core`` can be imported and used directly without starting the
framework runtime. Applications that want plugin discovery, process
orchestration, and agent lifecycle should use ``claia.framework`` on top.

``claia`` itself is an implicit (PEP 420) namespace package — there is no
top-level ``claia/__init__.py``. Each layer (``claia.core``,
``claia.framework``, ``claia.cli``) is independently installable.
"""

from .results import Result, DeploymentError
from .data import (
    BaseArtifact,
    TextArtifact,
    ImageArtifact,
    AudioArtifact,
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
    SolverInfo,
    PatternInfo,
    ProtocolInfo,
    ToolModuleInfo,
    ToolDefinition,
    ArgumentDefinition,
    ToolCallMatch,
    DeploymentParams,
    ParamSpec,
    ParamScope,
    SettingCategory,
)
from .definitions.model_definition import ModelDefinition
from .modality import (
    Modality,
    ChunkKind,
    GenerationChunk,
    text_chunk,
    iter_text,
)

__all__ = [
    # Results
    "Result", "DeploymentError",
    # Data
    "BaseArtifact", "TextArtifact", "ImageArtifact", "AudioArtifact", "Prompt",
    "Conversation", "Message",
    "DomainEvent", "EventType",
    # Plugin metadata + contracts
    "ExtensionInfo",
    "ArchitectureInfo", "DeploymentInfo", "SolverInfo",
    "PatternInfo", "ProtocolInfo", "ToolModuleInfo",
    "ToolDefinition", "ArgumentDefinition", "ToolCallMatch", "DeploymentParams",
    "ParamSpec", "ParamScope", "SettingCategory",
    "ModelDefinition",
    # Modality / multi-modal chunks
    "Modality", "ChunkKind", "GenerationChunk", "text_chunk", "iter_text",
]
