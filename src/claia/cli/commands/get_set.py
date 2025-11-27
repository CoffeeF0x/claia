"""
Get and Set command classes for the CLAIA CLI.

This module contains command classes for viewing and updating settings.
Delegates to cli.settings_* tools via the registry.
"""

import logging
from typing import List, Optional, Any, Dict

from claia.lib.results import Result
from .base import BaseCommand


logger = logging.getLogger(__name__)


class GetCommand(BaseCommand):
  """Command to view current settings. Delegates to cli.settings_get tool."""
  
  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """
    Execute the get command to display settings via cli.settings_get tool.
    
    Args:
        args: Optional list containing setting name to display
        conversation: Optional conversation context (unused)
    
    Returns:
        Result with setting information
    """
    self.logger.debug("Get command received")
    
    params: Dict[str, Any] = {'settings': self.settings}
    if args:
      params['setting_name'] = args[0]
    
    return self.registry.run_command('cli.settings_get', params, None)


class SetCommand(BaseCommand):
  """Command to update settings."""
  
  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """
    Execute the set command to update a setting.
    
    Args:
        args: List of arguments (either ["key=value"] or ["key", "value"])
        conversation: Optional conversation context (unused)
    
    Returns:
        Result indicating success/failure
    """
    self.logger.debug("Set command received")
    
    if not args:
      return Result(success=False, message="No setting provided. Usage: set <key> <value> or key=value")
    
    # Parse the arguments
    key, value = self._parse_set_args(args)
    
    if not key or value is None:
      return Result(success=False, message="Invalid syntax. Usage: set <key> <value> or set key=value")
    
    # Validate setting name
    if not self.settings.is_valid_setting(key):
      output = f"Unknown setting: {key}\n"
      output += f"Use {self.format_command('help')} to see available settings."
      return Result(success=False, message=output)
    
    # Update the setting
    success, message, old_value = self.settings.update_setting(key, value)
    
    if not success:
      self.logger.error(f"Error updating setting: {message}")
      return Result(success=False, message=message)
    
    # Get setting info for display
    key_normalized = key.lower().replace('-', '_')
    current_value, _, help_text, _ = self.settings.get_setting_info(key_normalized)
    display_value = self.settings._mask_sensitive_value(key_normalized, current_value)
    display_old = self.settings._mask_sensitive_value(key_normalized, old_value)
    
    # Update the registry's user_kwargs with the new setting value
    # This ensures that any code using the registry's kwargs gets the updated value
    self.registry.update_user_kwargs({key_normalized: current_value})
    self.logger.debug(f"Updated registry user_kwargs with new value for {key_normalized}")
    
    # Display confirmation
    output = f"\nSetting updated and saved:"
    output += f"\n  {key_normalized}: {display_old} -> {display_value}"
    if help_text:
      output += f"\n  ({help_text})"
    
    return Result(success=True, data=output)
  
  def _parse_set_args(self, args: List[str]) -> tuple:
    """
    Parse set command arguments.
    
    Args:
        args: List of arguments
    
    Returns:
        Tuple of (key, value)
    """
    if len(args) == 1 and '=' in args[0]:
      # Format: key=value
      key, value = args[0].split('=', 1)
      return key.strip(), value.strip()
    elif len(args) >= 2:
      # Format: key value (value may contain spaces)
      key = args[0]
      value = ' '.join(args[1:])
      return key, value
    else:
      return None, None

