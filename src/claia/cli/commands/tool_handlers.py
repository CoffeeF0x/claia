"""
Tool command handlers for the CLAIA CLI.

This module contains handlers for tool-related commands.
"""

import logging
from typing import List, Optional, Dict, Any

from claia.lib.results import Result


logger = logging.getLogger(__name__)


class ToolCommandsMixin:
  """Mixin class containing tool command handlers."""

  def _parse_kv_args(self, tokens: List[str]) -> Dict[str, Any]:
    """
    Parse a list of key=value tokens into a dict.

    Args:
        tokens: List of token strings

    Returns:
        Dictionary of parsed key-value pairs
    """
    params: Dict[str, Any] = {}
    for tok in tokens:
      if '=' in tok:
        k, v = tok.split('=', 1)
        params[k.strip()] = v.strip()
    return params


  def _cmd_tool(self, tokens: List[str], conversation: Optional[Any]) -> Result:
    """
    Execute a tool command via the registry.
    If no tokens provided, displays available modules.

    Args:
        tokens: Command tokens (first token is the tool name, rest are arguments)
        conversation: Optional conversation context

    Returns:
        Result from the tool execution
    """
    if not tokens:
      # Show available modules when no command provided
      catalog = self.registry.get_commands_catalog()
      if not catalog:
        output = "No modules available."
        return Result(success=True, data=output)
      
      output_lines = []
      output_lines.append("\nAvailable modules:")
      for mod_name, mod in catalog.items():
        info = mod.get('module_info')
        title = getattr(info, 'title', None) if info else None
        desc = getattr(info, 'description', None) if info else None
        line = f"  - {mod_name}"
        if title:
          line += f" ({title})"
        if desc:
          line += f": {desc}"
        output_lines.append(line)
      
      output_lines.append("\nUsage:")
      if self._current_mode == 'interactive':
        output_lines.append("  :tool <module>.<tool> [args]  - Execute a tool")
        output_lines.append("  :tool <module>                - List tools in a module")
      else:
        output_lines.append("  --tool <module>.<tool> [args]  - Execute a tool")
        output_lines.append("  --tool <module>                - List tools in a module")
      output_lines.append("")
      
      output = "\n".join(output_lines)
      return Result(success=True, data=output)

    cmd = tokens[0]
    tail_tokens = tokens[1:]
    
    # If only a module name was given (no dot), list its tools
    if '.' not in cmd and not tail_tokens:
      catalog = self.registry.get_commands_catalog()
      mod = catalog.get(cmd)
      if mod:
        output_lines = []
        output_lines.append(f"\nModule '{cmd}' tools:")
        for c in mod.get('list_of_tools', []):
          cname = c.get('tool_name')
          cdesc = c.get('tool_description')
          output_lines.append(f"  - {cmd}.{cname}: {cdesc}")
        output_lines.append("")
        output = "\n".join(output_lines)
        return Result(success=True, data=output)
      else:
        if self._current_mode == 'interactive':
          output = f"Unknown module: {cmd}\nUse ':tool' to see available modules."
        else:
          output = f"Unknown module: {cmd}\nUse '--tool' to see available modules."
        return Result(success=False, message=output)

    # Build params from key=value and collect positionals into __args__
    params = self._parse_kv_args(tail_tokens)
    pos_args = [t for t in tail_tokens if '=' not in t]
    if pos_args:
      params['__args__'] = pos_args

    # Get user configuration parameters
    user_kwargs = self.settings.get_user_kwargs()

    # Execute the command via registry
    try:
      result = self.registry.run_command(cmd, params, conversation, **user_kwargs)
      return result
    except Exception as e:
      logger.error(f"Error executing command '{cmd}': {e}", exc_info=True)
      return Result(success=False, message=f"Failed to execute command: {str(e)}")

