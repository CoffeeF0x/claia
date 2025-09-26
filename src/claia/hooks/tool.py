"""
Hook specifications for command module plugins.

A command module can implement multiple commands and exposes them through
a get_module_commands() method that returns a dictionary of CommandDefinition objects.
This allows a single module to efficiently handle multiple related commands.
"""

import pluggy
from dataclasses import dataclass
from typing import Optional, Dict, Any, Callable, List


@dataclass
class ArgumentDefinition:
  """Definition of a command argument."""
  name: str
  description: str
  data_type: str  # e.g., "str", "int", "float", "bool", "custom"
  required: bool = False
  default_value: Optional[Any] = None


@dataclass
class ToolDefinition:
  """Defines a tool within a module."""
  name: str
  description: str
  callable: Callable
  arguments: Dict[str, ArgumentDefinition]


@dataclass
class ToolModuleInfo:
  """Metadata for a tool module."""
  name: str
  title: str
  description: str
  required_args: Optional[List[str]] = None


hookspec = pluggy.HookspecMarker("claia_tool_modules")


class ToolModuleHooks:
  """Hook specs for tool module plugins."""

  @hookspec
  def get_module_info(self) -> ToolModuleInfo:
    """Return module info for registration and dispatch."""

  @hookspec
  def get_module_tools(self) -> Dict[str, ToolDefinition]:
    """
    Return a dictionary of available tools in this module.

    The key is the tool name, value is ToolDefinition.
    This allows a single module to provide multiple tools efficiently.
    """
