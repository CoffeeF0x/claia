"""
System commands (quit, help, version) for the CLAIA CLI.
"""

import logging
from typing import List, Optional, Any
from collections import defaultdict

from ...core.results import Result
from ...core.enums.plugins import ParamCategory
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
  
  def __init__(self, registry, settings, command_specs=None):
    super().__init__(registry, settings)
    self.command_specs = command_specs or []
  
  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """Execute the help command via cli.help tool with settings info."""
    params = {
      'registry': self.registry,
      'command_specs': self.command_specs,
    }
    
    result = self.registry.run_command('cli.help', params, None)
    if not result.is_success():
      return result
    
    # Append configuration settings help
    lines = [result.get_data() or "", "", "### Configuration"]
    lines.extend(self._get_settings_help())
    
    return Result(success=True, data="\n".join(lines), format="markdown")
  
  def _get_settings_help(self) -> List[str]:
    """Generate markdown help for configuration settings."""
    lines = [
      "",
      "Settings can be configured via:",
      "",
      "- Persisted: `claia set <setting> <value>` (view: `claia get`)",
      "- Command line: `--setting-name value` (this run only)",
      "- Environment: `CLAIA_SETTING_NAME=value`",
      "- `.env` file (default: `.env`)",
      "- `settings.json` (in files directory)",
      "",
    ]
    
    # Group settings by category (ParamSpec-driven).
    categorized = defaultdict(list)
    for spec in self.settings.config_specs.values():
      if not spec.externally_settable:
        continue
      help_desc = spec.description or ""
      setting_line = f"- `{spec.name}` — {help_desc}"
      category = spec.category if spec.category is not None else ParamCategory.MISC
      categorized[category].append(setting_line)

    for category in ParamCategory:
      if category in categorized:
        lines.append(f"**{category.value}**")
        lines.append("")
        lines.extend(categorized[category])
        lines.append("")
    
    lines.append("Use `claia help` to see this help message anytime.")
    
    return lines
