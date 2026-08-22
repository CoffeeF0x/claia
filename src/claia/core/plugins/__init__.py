"""
Plugin metadata and contracts for claia.core.

This subpackage defines:
- ``ExtensionInfo`` and per-plugin-type info dataclasses (data only).
- Helper dataclasses such as ``ToolDefinition`` and ``ServingPlan``.

The actual ABCs that implementations subclass live alongside their domain:
- ``claia.core.architectures.base.BaseArchitecture`` (architecture entry points)
- ``claia.core.deployments.base.BaseDeployment``
- ``claia.core.nodes.base.BaseNode``
- ``claia.core.definitions.base.BaseDefinitionProvider``
- ``claia.core.tools.protocols.base.BaseProtocol``
- ``claia.core.tools.modules.base.BaseToolModule``

The contracts in this subpackage stay framework-free so plugin metadata can
be imported without starting the runtime.
"""

from .base import (
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
)

__all__ = [
    "ExtensionInfo",
    "ArchitectureInfo",
    "DeploymentInfo",
    "NodeInfo",
    "ProtocolInfo",
    "ToolModuleInfo",
    "DefinitionsInfo",
    "ToolDefinition",
    "ArgumentDefinition",
    "ToolReference",
    "ServingPlan",
]
