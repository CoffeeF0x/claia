"""
Pluggy hookspecs for the CLAIA framework.

Each module in this package defines a ``*Hooks`` class that pluggy uses
for plugin discovery and dispatch. The data classes returned by these
hooks (``ArchitectureInfo``, ``DeploymentInfo``, ``ModelDefinition``,
``ToolDefinition``, etc.) live in ``claia_core.plugins.base`` so that
plugin implementations can construct them without depending on the
framework. They are re-exported here for convenience.
"""

from .base import ExtensionInfo
from .architecture import ArchitectureHooks, ArchitectureInfo
from .deployment import DeploymentHooks, DeploymentInfo
from .solver import SolverHooks, SolverInfo, DeploymentParams
from .definition import DefinitionHooks, ModelDefinition
from .pattern import PatternHooks, PatternInfo
from .protocol import ProtocolHooks, ProtocolInfo
from .tool import ToolModuleHooks, ToolModuleInfo, ToolDefinition, ArgumentDefinition
from .agent import AgentHooks, AgentInfo

__all__ = [
    'ExtensionInfo',
    'ArchitectureHooks', 'ArchitectureInfo',
    'DeploymentHooks', 'DeploymentInfo',
    'SolverHooks', 'SolverInfo', 'DeploymentParams',
    'DefinitionHooks', 'ModelDefinition',
    'PatternHooks', 'PatternInfo',
    'ProtocolHooks', 'ProtocolInfo',
    'ToolModuleHooks', 'ToolModuleInfo', 'ToolDefinition', 'ArgumentDefinition',
    'AgentHooks', 'AgentInfo',
]
