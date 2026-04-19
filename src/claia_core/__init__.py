"""
claia_core — the CLAIA library.

Pure data models, plugin contracts (ABCs), and concrete implementations of
model architectures, deployments, solvers, definitions, and tools.

claia_core has no framework dependencies (no pluggy, no IoC). It can be
imported and used directly without the claia framework. Applications that
want plugin discovery, process orchestration, and agent lifecycle should
use the ``claia`` framework package on top.
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
    ConversationSettings,
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
)
from .definitions.model_definition import ModelDefinition

__all__ = [
    # Results
    "Result", "DeploymentError",
    # Data
    "BaseArtifact", "TextArtifact", "ImageArtifact", "AudioArtifact", "Prompt",
    "Conversation", "Message", "ConversationSettings",
    "DomainEvent", "EventType",
    # Plugin metadata + contracts
    "ExtensionInfo",
    "ArchitectureInfo", "DeploymentInfo", "SolverInfo",
    "PatternInfo", "ProtocolInfo", "ToolModuleInfo",
    "ToolDefinition", "ArgumentDefinition", "ToolCallMatch", "DeploymentParams",
    "ModelDefinition",
]
