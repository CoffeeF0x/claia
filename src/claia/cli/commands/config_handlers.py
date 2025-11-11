"""
Configuration command handlers for the CLAIA CLI.

This module contains handlers for configuration-related commands like get, set, and setup.
"""

import logging
from typing import List

from claia.lib.results import Result
from claia.cli.settings import SettingCategory


logger = logging.getLogger(__name__)


class ConfigCommandsMixin:
  """Mixin class containing configuration command handlers."""

  def _cmd_get(self, args: List[str]) -> Result:
    """
    Handle get command - displays current settings.

    Args:
        args: Optional list containing setting name to display

    Returns:
        Result with setting information
    """
    logger.debug("Get command received")
    
    if args:
      # Get specific setting
      setting_name = args[0]
      current_value, default_value, help_text, category = self.settings.get_setting_info(setting_name)
      
      if current_value is None and not help_text:
        output = f"Unknown setting: {setting_name}\n"
        if self._current_mode == 'interactive':
          output += f"Use ':help' to see available settings."
        else:
          output += f"Use '--help' to see available settings."
        return Result(success=False, message=output)
      
      # Mask sensitive display
      display_value = self.settings._mask_sensitive_value(setting_name, current_value)
      
      output = f"\n{setting_name}: {display_value}"
      if help_text:
        output += f"\n  ({help_text})"
      
      return Result(success=True, data=output)
    
    else:
      # Display all settings grouped by category
      output_lines = []
      output_lines.append("\n" + "="*70)
      output_lines.append("CURRENT SETTINGS".center(70))
      output_lines.append("="*70 + "\n")
      
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
      
      output_lines.append("="*70)
      output = "\n".join(output_lines)
      return Result(success=True, data=output)


  def _cmd_set(self, args: List[str]) -> Result:
    """
    Handle set command - updates a setting and saves to file.

    Args:
        args: List of arguments (either ["key=value"] or ["key", "value"])

    Returns:
        Result indicating success/failure
    """
    logger.debug("Set command received")
    
    # Parse the arguments
    if len(args) == 1 and '=' in args[0]:
      # Format: key=value
      key, value = args[0].split('=', 1)
      key = key.strip()
      value = value.strip()
    elif len(args) >= 2:
      # Format: key value (value may contain spaces)
      key = args[0]
      value = ' '.join(args[1:])
    else:
      output = "Invalid syntax. Usage: set <key> <value> or set key=value"
      return Result(success=False, message=output)
    
    # Validate setting name
    if not self.settings.is_valid_setting(key):
      output = f"Unknown setting: {key}\n"
      if self._current_mode == 'interactive':
        output += f"Use ':help' to see available settings."
      else:
        output += f"Use '--help' to see available settings."
      return Result(success=False, message=output)
    
    # Update the setting using the Settings helper method
    success, message, old_value = self.settings.update_setting(key, value)
    
    if not success:
      logger.error(f"Error updating setting: {message}")
      return Result(success=False, message=message)
    
    # Get setting info for display
    key_normalized = key.lower().replace('-', '_')
    current_value, _, help_text, _ = self.settings.get_setting_info(key_normalized)
    display_value = self.settings._mask_sensitive_value(key_normalized, current_value)
    display_old = self.settings._mask_sensitive_value(key_normalized, old_value)
    
    # Display confirmation
    output = f"\nSetting updated and saved:"
    output += f"\n  {key_normalized}: {display_old} -> {display_value}"
    if help_text:
      output += f"\n  ({help_text})"
    
    return Result(success=True, data=output)


  def _cmd_setup(self) -> Result:
    """
    Handle setup command - interactive wizard for configuring API keys.

    Returns:
        Result indicating success/failure
    """
    logger.debug("Setup command received")
    
    print("\n" + "="*70)
    print("CLAIA SETUP WIZARD".center(70))
    print("="*70 + "\n")
    
    # Get list of unset API keys
    unset_keys = self.settings.get_unset_api_keys()
    
    if not unset_keys:
      print("✓ All API keys are configured!")
      print("\nYou can still update any settings using:")
      if self._current_mode == 'interactive':
        print("  :set <key> <value>  or  :get <key>\n")
      else:
        print("  --set <key> <value>  or  --get <key>\n")
      return Result(success=True, message="All API keys already configured")
    
    print("The following API keys are not configured:\n")
    for i, (var_name, help_text) in enumerate(unset_keys, 1):
      print(f"  {i}. {help_text} ({var_name})")
    
    print("\n" + "-"*70)
    print("\nYou can configure API keys in several ways:")
    if self._current_mode == 'interactive':
      print("  1. Interactively now (recommended for getting started)")
      print("  2. Using the ':set' command (e.g., :set openai_api_token YOUR_KEY)")
      print("  3. Setting environment variables (e.g., CLAIA_OPENAI_API_TOKEN)")
      print("  4. Adding them to your .env file")
    else:
      print("  1. Using the '--set' flag (e.g., --set openai_api_token YOUR_KEY)")
      print("  2. Setting environment variables (e.g., CLAIA_OPENAI_API_TOKEN)")
      print("  3. Adding them to your .env file")
      print("  4. Editing settings.json in your files directory")
    print("\n" + "-"*70)
    
    # Ask if user wants to configure keys now
    try:
      response = input("\nWould you like to configure API keys now? [y/N]: ").strip().lower()
      
      if response not in ('y', 'yes'):
        if self._current_mode == 'interactive':
          print("\nSetup cancelled. You can run ':setup' again anytime.")
          print("To suppress this notice on startup, run:")
          print("  :set suppress_setup_notice true\n")
        else:
          print("\nSetup cancelled.")
          print("To suppress this notice on startup, use:")
          print("  --set suppress_setup_notice true\n")
        return Result(success=True, message="Setup cancelled by user")
      
      print()
      configured_count = 0
      
      # Iterate through each unset key and prompt for value
      for var_name, help_text in unset_keys:
        print(f"\n{help_text} ({var_name}):")
        print("  (Press Enter to skip)")
        
        try:
          value = input("  Value: ").strip()
          
          if value:
            # Set the value using the existing set logic
            old_value = getattr(self.settings, var_name, "")
            setattr(self.settings, var_name, value)
            
            # Remove from CLI sourced settings if present
            if var_name in self.settings._cli_sourced_settings:
              self.settings._cli_sourced_settings.remove(var_name)
            
            # Mask display for security
            display_value = "***" + value[-4:] if len(value) > 4 else "***"
            print(f"  ✓ Set {var_name} to {display_value}")
            configured_count += 1
          else:
            print(f"  ⊘ Skipped {var_name}")
            
        except (KeyboardInterrupt, EOFError):
          print("\n\nSetup interrupted.")
          break
      
      # Save all configured settings
      if configured_count > 0:
        try:
          self.settings._save_settings_to_file()
          print(f"\n✓ Successfully configured {configured_count} API key(s)!")
        except Exception as e:
          print(f"\n✗ Error saving settings: {e}")
          logger.error(f"Error saving settings during setup: {e}", exc_info=True)
          return Result(success=False, message="Failed to save settings")
      
      print("\n" + "="*70)
      print("Setup complete! You can now use CLAIA with your configured APIs.")
      print("="*70 + "\n")
      
      return Result(success=True, message=f"Configured {configured_count} API key(s)")
      
    except (KeyboardInterrupt, EOFError):
      print("\n\nSetup cancelled.")
      return Result(success=True, message="Setup cancelled by user")

