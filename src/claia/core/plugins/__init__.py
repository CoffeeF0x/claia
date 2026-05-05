"""
Plugin metadata and contracts for claia.core.

This subpackage defines:
- ``ExtensionInfo`` and per-plugin-type info dataclasses (data only).
- Helper dataclasses such as ``ToolDefinition`` and ``DeploymentParams``.

The actual ABCs that implementations subclass live alongside their domain:
- ``claia.core.architectures.base.BaseArchitecture``
- ``claia.core.deployments.base.BaseDeployment``
- ``claia.core.solvers.base.BaseSolver``
- ``claia.core.tools.patterns.base.BasePattern``
- ``claia.core.tools.protocols.base.BaseProtocol``
- ``claia.core.tools.modules.base.BaseToolModule``

Pluggy hookspecs that mirror these ABCs live in ``claia.framework.hooks``.
The contracts in this subpackage stay framework-free so plugin metadata can
be imported without starting the runtime.
"""

from .base import (
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
    ToolReference,
    DeploymentParams,
)

__all__ = [
    "ExtensionInfo",
    "ArchitectureInfo",
    "DeploymentInfo",
    "SolverInfo",
    "PatternInfo",
    "ProtocolInfo",
    "ToolModuleInfo",
    "ToolDefinition",
    "ArgumentDefinition",
    "ToolCallMatch",
    "ToolReference",
    "DeploymentParams",
]
