"""
claia_cli — the CLAIA command-line application.

Implements the interactive REPL, ``setup``/``set``/``get`` configuration
commands, the JSON-file-backed conversation store, and the CLI-only
``WriterAgent`` that's registered programmatically against the
``Registry`` at startup.

While the repo is still a monorepo this package re-exports the most
commonly used framework + library symbols so callers can do::

    from claia_cli import Registry, Conversation, Result

without having to keep three import statements in sync. When the
packages eventually split into their own repos this convenience layer
will be replaced by direct imports from ``claia`` and ``claia_core``.
"""

# Library / framework convenience re-exports
from claia_core import (
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
from claia import (
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
