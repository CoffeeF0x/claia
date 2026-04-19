"""
Pluggy hookspecs for tool-module plugins.

These specs mirror ``BaseToolModule`` in
``claia_core.tools.modules.base``.
"""

import pluggy
from typing import Dict

from claia_core.plugins.base import (
    ToolModuleInfo,
    ToolDefinition,
    ArgumentDefinition,
)


hookspec = pluggy.HookspecMarker("claia_tool_modules")


class ToolModuleHooks:
  """Hook specifications for tool-module plugins."""

  @hookspec
  def get_module_info(self) -> ToolModuleInfo:
    """Return metadata describing this tool module."""

  @hookspec
  def get_module_tools(self) -> Dict[str, ToolDefinition]:
    """Return the tools provided by this module keyed by tool name."""


__all__ = [
    "ToolModuleHooks",
    "ToolModuleInfo",
    "ToolDefinition",
    "ArgumentDefinition",
]
