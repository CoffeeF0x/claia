"""
claia.cli — the CLAIA command-line application.

Implements the interactive REPL, ``setup``/``set``/``get`` configuration
commands, the JSON-file-backed conversation store, and the CLI-only
``WriterAgent`` that's registered programmatically against the
``Registry`` at startup.

For library use the canonical convenience hub is ``claia.framework`` —
e.g. ``from claia.framework import Registry, Conversation, Result``. The
re-exports below mirror that surface so CLI extension authors can pull
common types from a single module if they prefer.
"""

# Library / framework convenience re-exports
from claia.core import (
    Result,
    DeploymentError,
    Conversation,
    Message,
    ConversationSettings,
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
    SolverInfo,
    PatternInfo,
    ProtocolInfo,
    ToolModuleInfo,
    ToolDefinition,
    ArgumentDefinition,
    ToolCallMatch,
    DeploymentParams,
    ModelDefinition,
)
from claia.framework import (
    Registry,
    Process,
    ProcessQueue,
    BaseAgent,
)

__all__ = [
    # Framework
    "Registry", "Process", "ProcessQueue", "BaseAgent",
    # Library — results & conversation
    "Result", "DeploymentError",
    "Conversation", "Message", "ConversationSettings",
    "DomainEvent", "EventType",
    # Library — artifacts
    "BaseArtifact", "TextArtifact", "ImageArtifact", "AudioArtifact", "Prompt",
    # Library — plugin metadata
    "ExtensionInfo",
    "ArchitectureInfo", "DeploymentInfo", "SolverInfo",
    "PatternInfo", "ProtocolInfo", "ToolModuleInfo",
    "ToolDefinition", "ArgumentDefinition", "ToolCallMatch", "DeploymentParams",
    "ModelDefinition",
]
