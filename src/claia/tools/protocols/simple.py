"""
Simple protocol: resolve tool name to a command module plugin (supports grouped
commands via dotted names) and execute it, returning a common Result.
"""

import logging
from typing import Dict, Any
import pluggy

from claia.tools.hooks.protocol import ProtocolHooks, ProtocolInfo
from claia.common.results import Result

hookimpl = pluggy.HookimplMarker("claia_tool_protocols")
logger = logging.getLogger(__name__)


class SimpleProtocolPlugin:
  @hookimpl
  def get_protocol_info(self) -> ProtocolInfo:
    return ProtocolInfo(
      name="simple",
      title="Simple Local Protocol",
      description="Resolves tool name to a command module plugin and executes it.",
    )

  @hookimpl
  def execute(self, tool_name: str, parameters: Dict[str, Any], conversation, commands: Dict[str, Any], **kwargs) -> Result:
    """Execute a local command resolved from the provided commands catalog.

    The registry is responsible for preparing and validating parameters.
    This protocol simply locates the callable and invokes it.
    """
    # Resolve callable from catalog (supports 'module.command' or bare 'command')
    callable_fn = None

    try:
      if '.' in tool_name:
        module_name, cmd_name = tool_name.split('.', 1)
        mod = commands.get(module_name) if isinstance(commands, dict) else None
        if mod and isinstance(mod.get('list_of_commands'), list):
          for entry in mod['list_of_commands']:
            if entry.get('command_name') == cmd_name:
              callable_fn = entry.get('command_callable')
              break
      else:
        # Search all modules for the command
        if isinstance(commands, dict):
          for _, mod in commands.items():
            loc = mod.get('list_of_commands') if isinstance(mod, dict) else None
            if isinstance(loc, list):
              for entry in loc:
                if entry.get('command_name') == tool_name:
                  callable_fn = entry.get('command_callable')
                  break
            if callable_fn:
              break

      if not callable_fn:
        return Result.fail(f"Command '{tool_name}' not found")

      data = callable_fn(**(parameters or {}))
      return Result.ok(data)
    except Exception as e:
      logger.exception(f"Error executing command '{tool_name}'")
      return Result.fail(str(e))
