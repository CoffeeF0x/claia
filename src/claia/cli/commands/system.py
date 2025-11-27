"""
System command classes for the CLAIA CLI.

This module contains command classes for system-level operations like quit, help, and version.
"""

import logging
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
  """Command to display version information. Delegates to cli.version tool."""
  
  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """
    Execute the version command via cli.version tool.
    
    Args:
        args: Command arguments (unused)
        conversation: Optional conversation context (unused)
    
    Returns:
        Result with version information
    """
    self.logger.debug("Version command received")
    
    # Get user configuration parameters
    user_kwargs = self.settings.get_user_kwargs()
    
    # Call the cli.version tool through the registry
    return self.registry.run_command('cli.version', {}, None, **user_kwargs)


class HelpCommand(BaseCommand):
  """Command to display help information. Delegates to cli.help tool."""
  
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
    Execute the help command via cli.help tool.
    
    Note: This still includes settings help which requires CONFIG_VARS,
    so we generate a combined output from the tool and local settings.
    
    Args:
        args: Command arguments (unused)
        conversation: Optional conversation context (unused)
    
    Returns:
        Result with help information
    """
    self.logger.debug("Help command received")
    
    # Call the cli.help tool for commands and tools help
    params = {
      'registry': self.registry,
      'command_specs': self.command_specs,
      'current_mode': self._current_mode,
    }
    
    tool_result = self.registry.run_command('cli.help', params, None)
    
    if not tool_result.is_success():
      return tool_result
    
    help_text = [tool_result.get_data() or ""]
    
    # Add configuration settings help (requires CONFIG_VARS from settings module)
    help_text.append("")
    help_text.append("CONFIGURATION SETTINGS")
    help_text.append("-" * 70)
    help_text.extend(self._get_settings_help())
    help_text.append("")
    help_text.append("=" * 70)
    
    output = "\n".join(help_text)
    return Result(success=True, data=output)
  
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

