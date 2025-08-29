"""
Hook specifications for command module plugins.

A command module can implement multiple commands and exposes them through
a get_module_commands() method that returns a dictionary of CommandDefinition objects.
This allows a single module to efficiently handle multiple related commands.
"""

import pluggy
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Callable


@dataclass
class ArgumentDefinition:
  """Definition of a command argument."""
  name: str
  description: str
  data_type: str  # e.g., "str", "int", "float", "bool", "custom"
  required: bool = False
  default_value: Optional[Any] = None


@dataclass
class CommandDefinition:
  """Defines a command within a module."""
  name: str
  description: str
  callable: Callable
  arguments: Dict[str, ArgumentDefinition]


@dataclass
class CommandModuleInfo:
  """Metadata for a command module."""
  name: str
  title: str
  description: str
  required_args: Optional[List[str]] = None


hookspec = pluggy.HookspecMarker("claia_command_modules")


class CommandModuleHooks:
  """Hook specs for command module plugins."""

  @hookspec
  def get_module_info(self) -> CommandModuleInfo:
    """Return module info for registration and dispatch."""

  @hookspec
  def get_module_commands(self) -> Dict[str, CommandDefinition]:
    """
    Return a dictionary of available commands in this module.

    The key is the command name, value is CommandDefinition.
    This allows a single module to provide multiple commands efficiently.
    """

  @hookspec
  def run(self, parameters: Dict[str, Any], conversation, **kwargs) -> Any:
    """
    Execute this module with parameters (legacy single-command method).

    Return a string or dict value to be placed into the content, or a structured
    object the protocol/registry can turn into a string.

    Note: This method is kept for backward compatibility. New modules should
    implement get_module_commands() instead.
    """
