"""
Tool command class for the CLAIA CLI.

This module contains the command class for executing and listing tools.
"""

import logging
from typing import List, Optional, Any, Dict

from claia.lib.results import Result
from .base import BaseCommand


logger = logging.getLogger(__name__)


class ToolCommand(BaseCommand):
  """Command to execute and list available tools."""
  
  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """
    Execute a tool command via the registry.
    If no tokens provided, displays available modules.
    
    Args:
        args: Command arguments (first is tool name, rest are arguments)
        conversation: Optional conversation context
    
    Returns:
        Result from the tool execution
    """
    if not args:
      return self._list_modules()
    
    cmd = args[0]
    tail_tokens = args[1:]
    
    # If only a module name was given (no dot), list its tools
    if '.' not in cmd and not tail_tokens:
      return self._list_module_tools(cmd)
    
    # Execute the tool command
    return self._execute_tool(cmd, tail_tokens, conversation)
  
  def _list_modules(self) -> Result:
    """List all available modules."""
    catalog = self.registry.get_commands_catalog()
    
    if not catalog:
      return Result(success=True, data="No modules available.")
    
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
    prefix = self.get_help_prefix()
    output_lines.append(f"  {prefix}tool <module>.<tool> [args]  - Execute a tool")
    output_lines.append(f"  {prefix}tool <module>                - List tools in a module")
    output_lines.append("")
    
    output = "\n".join(output_lines)
    return Result(success=True, data=output)
  
  def _list_module_tools(self, module_name: str) -> Result:
    """
    List all tools in a specific module.
    
    Args:
        module_name: Name of the module
    
    Returns:
        Result with list of tools
    """
    catalog = self.registry.get_commands_catalog()
    mod = catalog.get(module_name)
    
    if not mod:
      output = f"Unknown module: {module_name}\n"
      output += f"Use {self.format_command('tool')} to see available modules."
      return Result(success=False, message=output)
    
    output_lines = []
    output_lines.append(f"\nModule '{module_name}' tools:")
    
    for c in mod.get('list_of_tools', []):
      cname = c.get('tool_name')
      cdesc = c.get('tool_description')
      output_lines.append(f"  - {module_name}.{cname}: {cdesc}")
    
    output_lines.append("")
    output = "\n".join(output_lines)
    return Result(success=True, data=output)
  
  def _execute_tool(self, cmd: str, tail_tokens: List[str], conversation: Optional[Any]) -> Result:
    """
    Execute a tool command.
    
    Args:
        cmd: Tool command (e.g., 'module.tool')
        tail_tokens: Additional arguments
        conversation: Optional conversation context
    
    Returns:
        Result from tool execution
    """
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
      self.logger.error(f"Error executing command '{cmd}': {e}", exc_info=True)
      return Result(success=False, message=f"Failed to execute command: {str(e)}")
  
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

