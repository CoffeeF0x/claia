"""
Plugin metadata and contracts for claia_core.

This subpackage defines:
- ``ExtensionInfo`` and per-plugin-type info dataclasses (data only).
- Helper dataclasses such as ``ToolDefinition`` and ``DeploymentParams``.

The actual ABCs that implementations subclass live alongside their domain:
- ``claia_core.architectures.base.BaseArchitecture``
- ``claia_core.deployments.base.BaseDeployment``
- ``claia_core.solvers.base.BaseSolver``
- ``claia_core.tools.patterns.base.BasePattern``
- ``claia_core.tools.protocols.base.BaseProtocol``
- ``claia_core.tools.modules.base.BaseToolModule``

Pluggy hookspecs that mirror these ABCs live in the ``claia.hooks`` framework
package; ``claia_core`` itself never imports pluggy.
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
    "DeploymentParams",
]
