"""
Get and Set command classes for the CLAIA CLI.

This module contains command classes for viewing and updating settings.
"""

import logging
from typing import List, Optional, Any

from claia.lib.results import Result
from claia.cli.settings import SettingCategory
from .base import BaseCommand


logger = logging.getLogger(__name__)


# Constants for formatted output
SETTINGS_HEADER = """
======================================================================
                         CURRENT SETTINGS                           
======================================================================
"""

SETTINGS_FOOTER = "=" * 70


class GetCommand(BaseCommand):
  """Command to view current settings."""
  
  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """
    Execute the get command to display settings.
    
    Args:
        args: Optional list containing setting name to display
        conversation: Optional conversation context (unused)
    
    Returns:
        Result with setting information
    """
    self.logger.debug("Get command received")
    
    if args:
      return self._get_single_setting(args[0])
    else:
      return self._get_all_settings()
  
  def _get_single_setting(self, setting_name: str) -> Result:
    """Get and display a single setting."""
    current_value, default_value, help_text, category = self.settings.get_setting_info(setting_name)
    
    if current_value is None and not help_text:
      output = f"Unknown setting: {setting_name}\n"
      output += f"Use {self.format_command('help')} to see available settings."
      return Result(success=False, message=output)
    
    # Mask sensitive display
    display_value = self.settings._mask_sensitive_value(setting_name, current_value)
    
    output = f"\n{setting_name}: {display_value}"
    if help_text:
      output += f"\n  ({help_text})"
    
    return Result(success=True, data=output)
  
  def _get_all_settings(self) -> Result:
    """Get and display all settings grouped by category."""
    output_lines = []
    output_lines.append(SETTINGS_HEADER)
    
    # Get settings grouped by category
    categorized = self.settings.get_all_settings_info()
    
    # Display settings by category
    for category in SettingCategory:
      if category in categorized:
        output_lines.append(f"{category.value}:")
        output_lines.append("-" * 70)
        for var_name, display_value, help_text in categorized[category]:
          output_lines.append(f"  {var_name:30s} = {display_value}")
        output_lines.append("")
    
    output_lines.append(SETTINGS_FOOTER)
    output = "\n".join(output_lines)
    return Result(success=True, data=output)


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

