"""
Tool command for executing and listing tools.
"""

import logging
from typing import List, Optional, Any, Dict

from claia_core.results import Result
from .base import BaseCommand


logger = logging.getLogger(__name__)


class ToolCommand(BaseCommand):
  """Command to execute and list available tools."""
  
  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """Execute a tool or list modules/tools."""
    if not args:
      return self._list_modules()
    
    cmd = args[0]
    tail = args[1:]
    
    # If only module name (no dot, no args), list its tools
    if '.' not in cmd and not tail:
      return self._list_module_tools(cmd)
    
    return self._execute_tool(cmd, tail, conversation)
  
  def _list_modules(self) -> Result:
    """List all available modules."""
    catalog = self.registry.get_commands_catalog()
    if not catalog:
      return Result(success=True, data="No modules available.")
    
    prefix = self.get_help_prefix()
    lines = ["\nAvailable modules:"]
    
    for mod_name, mod in catalog.items():
      info = mod.get('module_info')
      title = getattr(info, 'title', None) if info else None
      desc = getattr(info, 'description', None) if info else None
      
      line = f"  - {mod_name}"
      if title:
        line += f" ({title})"
      if desc:
        line += f": {desc}"
      lines.append(line)
    
    lines.extend([
      "\nUsage:",
      f"  {prefix}tool <module>.<tool> [args]  - Execute a tool",
      f"  {prefix}tool <module>                - List tools in a module",
      ""
    ])
    return Result(success=True, data="\n".join(lines))
  
  def _list_module_tools(self, module_name: str) -> Result:
    """List all tools in a specific module."""
    catalog = self.registry.get_commands_catalog()
    mod = catalog.get(module_name)
    
    if not mod:
      return Result(success=False, message=f"Unknown module: {module_name}\nUse {self.format_command('tool')} to see available modules.")
    
    lines = [f"\nModule '{module_name}' tools:"]
    for tool in mod.get('list_of_tools', []):
      lines.append(f"  - {module_name}.{tool.get('tool_name')}: {tool.get('tool_description')}")
    lines.append("")
    
    return Result(success=True, data="\n".join(lines))
  
  def _execute_tool(self, cmd: str, tail: List[str], conversation: Optional[Any]) -> Result:
    """Execute a tool command."""
    params = {k.strip(): v.strip() for t in tail if '=' in t for k, v in [t.split('=', 1)]}
    pos_args = [t for t in tail if '=' not in t]
    if pos_args:
      params['__args__'] = pos_args
    
    user_kwargs = self.settings.get_user_kwargs()
    
    try:
      return self.registry.run_command(cmd, params, conversation, **user_kwargs)
    except Exception as e:
      self.logger.error(f"Error executing command '{cmd}': {e}", exc_info=True)
      return Result(success=False, message=f"Failed to execute command: {str(e)}")
