"""
claia.cli — the CLAIA command-line application.

Implements the one-shot command surface (``claia <command> [args…]``),
the ``setup``/``set``/``get`` configuration commands, the
JSON-file-backed conversation store, and the CLI-only ``WriterAgent``
that's registered programmatically against the ``Registry`` at startup.

For library use the canonical convenience hub is ``claia.framework`` —
e.g. ``from claia.framework import Registry, Conversation, Result``. The
re-exports below mirror that surface so CLI extension authors can pull
common types from a single module if they prefer.
"""

# Library / framework convenience re-exports
from ..core import (
    Result,
    DeploymentError,
    ResolveError,
    Conversation,
    Message,
    DomainEvent,
    EventType,
    BaseArtifact,
    TextArtifact,
    ImageArtifact,
    AudioArtifact,
    Prompt,
    ExtensionInfo,
    ArchitectureInfo,
    DeploymentInfo,
    NodeInfo,
    ProtocolInfo,
    ToolModuleInfo,
    ToolDefinition,
    ArgumentDefinition,
    ToolReference,
    ServingPlan,
    ParamSpec,
    ParamScope,
    ParamCategory,
    ModelDefinition,
)
from ..framework import (
    Registry,
    Task,
    TaskQueue,
    BaseAgent,
)

__all__ = [
    # Framework
    "Registry", "Task", "TaskQueue", "BaseAgent",
    # Library — results & conversation
    "Result", "DeploymentError", "ResolveError",
    "Conversation", "Message",
    "DomainEvent", "EventType",
    # Library — artifacts
    "BaseArtifact", "TextArtifact", "ImageArtifact", "AudioArtifact", "Prompt",
    # Library — plugin metadata
    "ExtensionInfo",
    "ArchitectureInfo", "DeploymentInfo", "NodeInfo",
    "ProtocolInfo", "ToolModuleInfo",
    "ToolDefinition", "ArgumentDefinition", "ToolReference", "ServingPlan",
    "ParamSpec", "ParamScope", "ParamCategory",
    "ModelDefinition",
]
