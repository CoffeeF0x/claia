"""
Get and Set commands for viewing and updating settings.
"""

import logging
from typing import List, Optional, Any, Dict

from claia.core.results import Result
from .base import BaseCommand


logger = logging.getLogger(__name__)


class GetCommand(BaseCommand):
  """Command to view current settings."""
  
  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """Display settings via cli.settings_get tool."""
    params: Dict[str, Any] = {'settings': self.settings}
    if args:
      params['setting_name'] = args[0]
    return self.registry.run_command('cli.settings_get', params, None)


class SetCommand(BaseCommand):
  """Command to update settings."""
  
  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """Update a setting value."""
    if not args:
      return Result(success=False, message="No setting provided. Usage: set <key> <value> or key=value")
    
    key, value = self._parse_args(args)
    if not key or value is None:
      return Result(success=False, message="Invalid syntax. Usage: set <key> <value> or set key=value")
    
    if not self.settings.is_valid_setting(key):
      return Result(success=False, message=f"Unknown setting: {key}\nUse {self.format_command('help')} to see available settings.")
    
    success, message, old_value = self.settings.update_setting(key, value)
    if not success:
      return Result(success=False, message=message)
    
    # Get display values
    key_normalized = key.lower().replace('-', '_')
    current_value, _, help_text, _ = self.settings.get_setting_info(key_normalized)
    display_value = self.settings._mask_sensitive_value(key_normalized, current_value)
    display_old = self.settings._mask_sensitive_value(key_normalized, old_value)
    
    # Update registry kwargs
    self.registry.update_user_kwargs({key_normalized: current_value})
    
    output = f"\nSetting updated and saved:\n  {key_normalized}: {display_old} -> {display_value}"
    if help_text:
      output += f"\n  ({help_text})"
    
    return Result(success=True, data=output)
  
  def _parse_args(self, args: List[str]) -> tuple:
    """Parse set command arguments into (key, value)."""
    if len(args) == 1 and '=' in args[0]:
      key, value = args[0].split('=', 1)
      return key.strip(), value.strip()
    if len(args) >= 2:
      return args[0], ' '.join(args[1:])
    return None, None


class ResetCommand(BaseCommand):
  """
  Clear a setting back to its default.

  Usage:
    reset <key>           Clear a single setting
    reset --runtime       Clear every RUNTIME-scoped setting (so models
                          fall back to their declared defaults)
  """

  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    if not args:
      return Result(success=False, message="No setting provided. Usage: reset <key> | reset --runtime")

    if args[0] in ("--runtime", "-r"):
      changed = self.settings.reset_runtime_settings()
      for name in changed:
        self.registry.update_user_kwargs({name: getattr(self.settings, name, None)})
      if not changed:
        return Result(success=True, data="No runtime settings were overridden.")
      bullets = "\n  - ".join(changed)
      return Result(success=True, data=f"\nReset {len(changed)} runtime setting(s):\n  - {bullets}")

    key = args[0]
    if not self.settings.is_valid_setting(key):
      return Result(success=False, message=f"Unknown setting: {key}")

    success, message, old_value = self.settings.reset_setting(key)
    if not success:
      return Result(success=False, message=message)

    key_normalized = key.lower().replace('-', '_')
    current_value, _, help_text, _ = self.settings.get_setting_info(key_normalized)
    display_old = self.settings._mask_sensitive_value(key_normalized, old_value)
    display_new = self.settings._mask_sensitive_value(key_normalized, current_value)

    self.registry.update_user_kwargs({key_normalized: current_value})

    output = f"\nSetting reset:\n  {key_normalized}: {display_old} -> {display_new}"
    if help_text:
      output += f"\n  ({help_text})"
    return Result(success=True, data=output)
