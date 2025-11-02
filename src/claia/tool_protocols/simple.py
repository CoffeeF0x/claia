"""
Simple protocol: resolve tool name to a command module plugin (supports grouped
commands via dotted names) and execute it, returning a common Result.
"""

import logging
from typing import Dict, Any
import pluggy

from claia.hooks.protocol import ProtocolHooks, ProtocolInfo
from claia.lib.results import Result

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
    
    Tool callables must return either:
    - A Result object (used as-is)
    - A string (wrapped in Result.ok)
    - Otherwise an error is returned
    """
    # Resolve callable from catalog (supports 'module.command' or bare 'command')
    callable_fn = None

    try:
      if '.' in tool_name:
        module_name, cmd_name = tool_name.split('.', 1)
        mod = commands.get(module_name) if isinstance(commands, dict) else None
        if mod and isinstance(mod.get('list_of_tools'), list):
          for entry in mod['list_of_tools']:
            if entry.get('tool_name') == cmd_name:
              callable_fn = entry.get('tool_callable')
              break
      else:
        # Search all modules for the tool
        if isinstance(commands, dict):
          for _, mod in commands.items():
            loc = mod.get('list_of_tools') if isinstance(mod, dict) else None
            if isinstance(loc, list):
              for entry in loc:
                if entry.get('tool_name') == tool_name:
                  callable_fn = entry.get('tool_callable')
                  break
            if callable_fn:
              break

      if not callable_fn:
        return Result.fail(f"Tool '{tool_name}' not found")

      result = callable_fn(**(parameters or {}))
      
      # Handle different return types from tool callables
      if isinstance(result, Result):
        # Tool returned a Result object, use it directly
        return result
      elif isinstance(result, str):
        # Tool returned a string, wrap it in Result.ok
        return Result.ok(result)
      else:
        # Invalid return type
        return Result.fail(f"Tool '{tool_name}' returned invalid type: {type(result).__name__}. Tools must return Result or str.")
    except Exception as e:
      logger.exception(f"Error executing tool '{tool_name}'")
      return Result.fail(str(e))
