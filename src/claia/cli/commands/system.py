"""
System command classes for the CLAIA CLI.

This module contains command classes for system-level operations like quit, help, and version.
"""

import sys
import logging
import importlib.metadata as importlib_metadata
from typing import List, Optional, Any
from collections import defaultdict

from claia.lib.results import Result
from claia.cli.settings import CONFIG_VARS, SettingCategory
from .base import BaseCommand


logger = logging.getLogger(__name__)


# Help text constant for cleaner code
HELP_HEADER = """
======================================================================
                             CLAIA HELP                              
======================================================================
"""

HELP_FOOTER = """
======================================================================
"""


class QuitCommand(BaseCommand):
  """Command to exit the application."""
  
  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """
    Execute the quit command by calling system.exit tool.
    
    Args:
        args: Command arguments (unused)
        conversation: Optional conversation context (unused)
    
    Returns:
        Result with exit flag set
    """
    self.logger.info("Quit command received")
    
    # Get user configuration parameters
    user_kwargs = self.settings.get_user_kwargs()
    
    # Call the system.exit tool through the registry
    try:
      result = self.registry.run_command('system.exit', {}, None, **user_kwargs)
      return result
    except Exception as e:
      self.logger.error(f"Error calling system.exit: {e}", exc_info=True)
      # Fallback to direct exit result if system.exit fails
      return Result(success=True, message="Goodbye!", exit_code=0)


class VersionCommand(BaseCommand):
  """Command to display version information."""
  
  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """
    Execute the version command.
    
    Args:
        args: Command arguments (unused)
        conversation: Optional conversation context (unused)
    
    Returns:
        Result with version information
    """
    self.logger.debug("Version command received")
    
    try:
      version = importlib_metadata.version("claia")
    except importlib_metadata.PackageNotFoundError:
      version = "dev"
    except Exception:
      version = "unknown"
    
    version_text = f"CLAIA version {version}"
    version_text += f"\nPython {sys.version.split()[0]}"
    version_text += f"\nPlatform: {sys.platform}"
    
    return Result(success=True, data=version_text)


class HelpCommand(BaseCommand):
  """Command to display help information."""
  
  def __init__(self, registry, settings, current_mode='interactive', command_specs=None):
    """
    Initialize the help command.
    
    Args:
        registry: The unified registry
        settings: The settings object
        current_mode: Current execution mode
        command_specs: List of command specifications for help display
    """
    super().__init__(registry, settings, current_mode)
    self.command_specs = command_specs or []
  
  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """
    Execute the help command.
    
    Args:
        args: Command arguments (unused)
        conversation: Optional conversation context (unused)
    
    Returns:
        Result with help information
    """
    self.logger.debug("Help command received")
    
    help_text = []
    help_text.append(HELP_HEADER)
    
    # Built-in Commands
    help_text.append("BUILT-IN COMMANDS")
    help_text.append("-" * 70)
    help_text.extend(self._get_commands_help())
    help_text.append("")
    
    # Available Tools/Modules
    help_text.append("AVAILABLE TOOLS & MODULES")
    help_text.append("-" * 70)
    help_text.extend(self._get_tools_help())
    help_text.append("")
    
    # Configuration Settings
    help_text.append("CONFIGURATION SETTINGS")
    help_text.append("-" * 70)
    help_text.extend(self._get_settings_help())
    
    help_text.append(HELP_FOOTER)
    
    output = "\n".join(help_text)
    return Result(success=True, data=output)
  
  def _get_commands_help(self) -> List[str]:
    """Generate help text for built-in commands."""
    lines = []
    
    if self._current_mode == 'interactive':
      lines.append("  Commands (prefix with ':'):")
      for aliases, _, help_desc, _, _, _ in self.command_specs:
        aliases_str = ', '.join(aliases)
        lines.append(f"    :{aliases_str:24s} - {help_desc}")
    else:
      lines.append("  Command Line Flags:")
      from .specs import generate_cli_alias
      for aliases, _, help_desc, _, _, _ in self.command_specs:
        cli_aliases = [generate_cli_alias(alias) for alias in aliases]
        aliases_str = ', '.join(cli_aliases)
        lines.append(f"    {aliases_str:25s} - {help_desc}")
    
    return lines
  
  def _get_tools_help(self) -> List[str]:
    """Generate help text for available tools and modules."""
    lines = []
    catalog = self.registry.get_commands_catalog()
    
    if catalog:
      total_tools = 0
      for mod_name, mod in catalog.items():
        info = mod.get('module_info')
        title = getattr(info, 'title', None) if info else None
        desc = getattr(info, 'description', None) if info else None
        
        # Module header
        line = f"  [{mod_name}]"
        if title:
          line += f" {title}"
        lines.append(line)
        if desc:
          lines.append(f"    {desc}")
        
        # List tools in this module
        tools = mod.get('list_of_tools', [])
        if tools:
          for tool in tools:
            tool_name = tool.get('tool_name')
            tool_desc = tool.get('tool_description', '')
            lines.append(f"    • {mod_name}.{tool_name:20s} - {tool_desc}")
            total_tools += 1
        else:
          lines.append(f"    (no tools available)")
        lines.append("")
      
      lines.append(f"  Total: {len(catalog)} module(s), {total_tools} tool(s)")
    else:
      lines.append("  No modules loaded")
    
    return lines
  
  def _get_settings_help(self) -> List[str]:
    """Generate help text for configuration settings."""
    lines = []
    lines.append("  Settings can be configured via:")
    
    if self._current_mode == 'interactive':
      lines.append("    • Interactive commands: :get <setting> or :set <setting> <value>")
      lines.append("    • Command line: --setting-name value (when launching)")
      lines.append("    • Environment: CLAIA_SETTING_NAME=value")
      lines.append("    • .env file (default: .env)")
      lines.append("    • settings.json (in files directory)")
      lines.append("")
      lines.append("  Use ':get' to view current values, ':set <name> <value>' to change.")
    else:
      lines.append("    • Command line: --setting-name value")
      lines.append("    • Environment: CLAIA_SETTING_NAME=value")
      lines.append("    • .env file (default: .env)")
      lines.append("    • settings.json (in files directory)")
      lines.append("")
      lines.append("  Note: the settings below are not saved to the settings.json file.")
      lines.append("        please use one of the other methods to save your settings.")
    lines.append("")
    
    # Group settings by category
    categorized_settings = defaultdict(list)
    
    for var_name, default, externally_settable, category, help_desc in CONFIG_VARS:
      if externally_settable:
        if self._current_mode == 'interactive':
          setting_line = f"    {var_name:30s} {help_desc}"
        else:
          cli_name = var_name.replace('_', '-')
          setting_line = f"    --{cli_name:30s} {help_desc}"
        categorized_settings[category].append(setting_line)
    
    # Display settings grouped by category
    for category in SettingCategory:
      if category in categorized_settings:
        lines.append(f"  {category.value}:")
        lines.extend(categorized_settings[category])
        lines.append("")
    
    # Show appropriate help command
    if self._current_mode == 'interactive':
      lines.append("  Use ':help' or ':h' to see this help message anytime.")
    else:
      lines.append("  Use '--help' or '-h' to see this help message anytime.")
    
    return lines

