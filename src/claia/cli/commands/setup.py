"""
Setup command class for the CLAIA CLI.

This module contains the interactive setup wizard for configuring API keys.
"""

import logging
from typing import List, Optional, Any

from claia.lib.results import Result
from .base import BaseCommand


logger = logging.getLogger(__name__)


# Constants for setup wizard
SETUP_HEADER = """
======================================================================
                        CLAIA SETUP WIZARD                          
======================================================================
"""

SETUP_DIVIDER = "-" * 70

SETUP_FOOTER = """
======================================================================
Setup complete! You can now use CLAIA with your configured APIs.
======================================================================
"""


class SetupCommand(BaseCommand):
  """Interactive setup wizard command for API keys and configuration."""
  
  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """
    Execute the setup command - interactive wizard for configuring API keys.
    
    Args:
        args: Command arguments (unused)
        conversation: Optional conversation context (unused)
    
    Returns:
        Result indicating success/failure
    """
    self.logger.debug("Setup command received")
    
    print(SETUP_HEADER)
    
    # Get list of unset API keys
    unset_keys = self.settings.get_unset_api_keys()
    
    if not unset_keys:
      return self._handle_all_configured()
    
    self._display_unset_keys(unset_keys)
    self._display_configuration_methods()
    
    # Ask if user wants to configure keys now
    try:
      response = input("\nWould you like to configure API keys now? [y/N]: ").strip().lower()
      
      if response not in ('y', 'yes'):
        return self._handle_setup_cancelled()
      
      print()
      configured_count = self._configure_keys(unset_keys)
      
      # Save all configured settings
      if configured_count > 0:
        try:
          self.settings._save_settings_to_file()
          print(f"\n✓ Successfully configured {configured_count} API key(s)!")
        except Exception as e:
          print(f"\n✗ Error saving settings: {e}")
          self.logger.error(f"Error saving settings during setup: {e}", exc_info=True)
          return Result(success=False, message="Failed to save settings")
      
      print(SETUP_FOOTER)
      return Result(success=True, message=f"Configured {configured_count} API key(s)")
      
    except (KeyboardInterrupt, EOFError):
      print("\n\nSetup cancelled.")
      return Result(success=True, message="Setup cancelled by user")
  
  def _handle_all_configured(self) -> Result:
    """Handle the case where all API keys are already configured."""
    print("✓ All API keys are configured!")
    print("\nYou can still update any settings using:")
    
    if self._current_mode == 'interactive':
      print("  :set <key> <value>  or  :get <key>\n")
    else:
      print("  --set <key> <value>  or  --get <key>\n")
    
    return Result(success=True, message="All API keys already configured")
  
  def _display_unset_keys(self, unset_keys: List[tuple]) -> None:
    """Display the list of unset API keys."""
    print("The following API keys are not configured:\n")
    for i, (var_name, help_text) in enumerate(unset_keys, 1):
      print(f"  {i}. {help_text} ({var_name})")
    print(f"\n{SETUP_DIVIDER}")
  
  def _display_configuration_methods(self) -> None:
    """Display available configuration methods."""
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
    
    print(f"\n{SETUP_DIVIDER}")
  
  def _handle_setup_cancelled(self) -> Result:
    """Handle the case where user cancels setup."""
    if self._current_mode == 'interactive':
      print("\nSetup cancelled. You can run ':setup' again anytime.")
      print("To suppress this notice on startup, run:")
      print("  :set suppress_setup_notice true\n")
    else:
      print("\nSetup cancelled.")
      print("To suppress this notice on startup, use:")
      print("  --set suppress_setup_notice true\n")
    
    return Result(success=True, message="Setup cancelled by user")
  
  def _configure_keys(self, unset_keys: List[tuple]) -> int:
    """
    Interactively configure each unset API key.
    
    Args:
        unset_keys: List of (var_name, help_text) tuples
    
    Returns:
        Number of keys successfully configured
    """
    configured_count = 0
    
    for var_name, help_text in unset_keys:
      print(f"\n{help_text} ({var_name}):")
      print("  (Press Enter to skip)")
      
      try:
        value = input("  Value: ").strip()
        
        if value:
          # Set the value
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
    
    return configured_count

