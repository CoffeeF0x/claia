"""
System commands (quit, help, version) for the CLAIA CLI.
"""

import logging
from typing import List, Optional, Any
from collections import defaultdict

from ...core.results import Result
from ...core.enums.plugins import SettingCategory
from .base import BaseCommand


logger = logging.getLogger(__name__)


class QuitCommand(BaseCommand):
  """Command to exit the application."""
  
  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """Execute the quit command by calling system.exit tool."""
    self.logger.info("Quit command received")
    user_kwargs = self.settings.get_user_kwargs()
    
    try:
      return self.registry.run_command('system.exit', {}, None, **user_kwargs)
    except Exception as e:
      self.logger.error(f"Error calling system.exit: {e}", exc_info=True)
      return Result(success=True, message="Goodbye!", exit_code=0)


class VersionCommand(BaseCommand):
  """Command to display version information."""
  
  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """Execute the version command via cli.version tool."""
    user_kwargs = self.settings.get_user_kwargs()
    return self.registry.run_command('cli.version', {}, None, **user_kwargs)


class HelpCommand(BaseCommand):
  """Command to display help information."""
  
  def __init__(self, registry, settings, current_mode='interactive', command_specs=None):
    super().__init__(registry, settings, current_mode)
    self.command_specs = command_specs or []
  
  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """Execute the help command via cli.help tool with settings info."""
    params = {
      'registry': self.registry,
      'command_specs': self.command_specs,
      'current_mode': self._current_mode,
    }
    
    result = self.registry.run_command('cli.help', params, None)
    if not result.is_success():
      return result
    
    # Append configuration settings help
    lines = [result.get_data() or "", "", "CONFIGURATION SETTINGS", "-" * 70]
    lines.extend(self._get_settings_help())
    lines.extend(["", "=" * 70])
    
    return Result(success=True, data="\n".join(lines))
  
  def _get_settings_help(self) -> List[str]:
    """Generate help text for configuration settings."""
    lines = ["  Settings can be configured via:"]
    is_interactive = self._current_mode == 'interactive'
    
    if is_interactive:
      lines.extend([
        "    • Interactive commands: :get <setting> or :set <setting> <value>",
        "    • Command line: --setting-name value (when launching)",
        "    • Environment: CLAIA_SETTING_NAME=value",
        "    • .env file (default: .env)",
        "    • settings.json (in files directory)",
        "",
        "  Use ':get' to view current values, ':set <name> <value>' to change."
      ])
    else:
      lines.extend([
        "    • Command line: --setting-name value",
        "    • Environment: CLAIA_SETTING_NAME=value",
        "    • .env file (default: .env)",
        "    • settings.json (in files directory)",
        "",
        "  Note: the settings below are not saved to the settings.json file.",
        "        please use one of the other methods to save your settings."
      ])
    
    lines.append("")
    
    # Group settings by category (ParamSpec-driven).
    categorized = defaultdict(list)
    for spec in self.settings.config_specs.values():
      if not spec.externally_settable:
        continue
      help_desc = spec.description or ""
      if is_interactive:
        setting_line = f"    {spec.name:30s} {help_desc}"
      else:
        cli_name = spec.name.replace('_', '-')
        setting_line = f"    --{cli_name:30s} {help_desc}"
      category = spec.category if spec.category is not None else SettingCategory.MISC
      categorized[category].append(setting_line)

    for category in SettingCategory:
      if category in categorized:
        lines.append(f"  {category.value}:")
        lines.extend(categorized[category])
        lines.append("")
    
    help_cmd = ":help" if is_interactive else "--help"
    lines.append(f"  Use '{help_cmd}' to see this help message anytime.")
    
    return lines
