"""
claia.framework — the CLAIA orchestration runtime.

Provides the inversion-of-control runtime on top of ``claia.core``:

- ``Manager`` discovers plugins via pluggy entry points (architectures,
  deployments, solvers, definitions, tool patterns/protocols/modules,
  agents).
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

Quick library example::

    from claia.framework import Registry, Conversation

    registry = Registry()
    registry.load_plugins(openai_api_token="sk-...")
    registry.start_workers(2)

    conv = Conversation()
    conv.add_message_from_role("user", "Hello!")
    result = registry.run("gpt-4", conv)
    print(result.get_data())

Streaming::

    for token in registry.run("gpt-4", conv, streaming=True):
        print(token, end="", flush=True)

Callback-style query::

    result = registry.query(
        "gpt-4", "Hello!",
        on_token=lambda t: print(t, end="", flush=True),
    )
"""

# Re-exports from claia.core for convenience.
from claia.core.results import Result, DeploymentError
from claia.core.data import (
    Conversation,
    Message,
    ConversationSettings,
    BaseArtifact,
    TextArtifact,
    ImageArtifact,
    AudioArtifact,
    Prompt,
    DomainEvent,
    EventType,
)
from claia.core.plugins.base import (
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
from claia.core.definitions.model_definition import ModelDefinition

# Framework primitives.
from .process import Process
from .queue import ProcessQueue
from .registry import Registry
from .manager import Manager
from .agents.base import BaseAgent

__all__ = [
    # Framework primitives
    "Registry", "Manager", "Process", "ProcessQueue", "BaseAgent",
    # Results
    "Result", "DeploymentError",
    # Data
    "Conversation", "Message", "ConversationSettings",
    "BaseArtifact", "TextArtifact", "ImageArtifact", "AudioArtifact", "Prompt",
    "DomainEvent", "EventType",
    # Plugin metadata
    "ExtensionInfo",
    "ArchitectureInfo", "DeploymentInfo", "SolverInfo",
    "PatternInfo", "ProtocolInfo", "ToolModuleInfo",
    "ToolDefinition", "ArgumentDefinition", "ToolCallMatch", "DeploymentParams",
    "ModelDefinition",
]
