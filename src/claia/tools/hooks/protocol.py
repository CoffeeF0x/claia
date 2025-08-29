"""
Hook specifications for tool protocol plugins.

A protocol plugin knows how to resolve a tool name to an executable
command module (or remote tool) and invoke it.
"""

import pluggy
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from claia.common.results import Result


@dataclass
class ProtocolInfo:
  name: str
  title: str
  description: str
  required_args: Optional[List[str]] = None


hookspec = pluggy.HookspecMarker("claia_tool_protocols")


class ProtocolHooks:
  """Hook specifications for tool protocol plugins."""

  @hookspec
  def get_protocol_info(self) -> ProtocolInfo:
    """Return information about this protocol plugin."""

  @hookspec
  def execute(self, tool_name: str, parameters: Dict[str, Any], conversation, manager, **kwargs) -> Result:
    """
    Execute a tool by name with given parameters under this protocol.

    - conversation: the Conversation instance
    - manager: the ToolsManager (for accessing command modules or other resources)
    - kwargs: user/system kwargs filtered via required_args at the registry level

    Returns:
      Result: success indicates execution ok; data contains the tool's return value (string, dict, etc.);
              message contains any error on failure.
    """
