"""
Setup command for interactive API key configuration.
"""

import logging
from typing import List, Optional, Any

from ...core.results import Result
from .base import BaseCommand


logger = logging.getLogger(__name__)

SETUP_HEADER = """
======================================================================
                        CLAIA SETUP WIZARD                          
======================================================================
"""

SETUP_FOOTER = """
======================================================================
Setup complete! You can now use CLAIA with your configured APIs.
======================================================================
"""


class SetupCommand(BaseCommand):
  """Interactive setup wizard for API keys and configuration."""
  
  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """Run the interactive setup wizard."""
    print(SETUP_HEADER)
    
    unset_keys = self.settings.get_unset_api_keys()
    
    if not unset_keys:
      return self._all_configured()
    
    self._display_unset_keys(unset_keys)
    self._display_config_methods()
    
    try:
      response = input("\nWould you like to configure API keys now? [y/N]: ").strip().lower()
      
      if response not in ('y', 'yes'):
        return self._setup_cancelled()
      
      print()
      count = self._configure_keys(unset_keys)
      
      if count > 0:
        try:
          self.settings._save_settings_to_file()
          print(f"\n✓ Successfully configured {count} API key(s)!")
        except Exception as e:
          self.logger.error(f"Error saving settings: {e}", exc_info=True)
          return Result(success=False, message="Failed to save settings")
      
      print(SETUP_FOOTER)
      return Result(success=True, message=f"Configured {count} API key(s)")
      
    except (KeyboardInterrupt, EOFError):
      print("\n\nSetup cancelled.")
      return Result(success=True, message="Setup cancelled by user")
  
  def _all_configured(self) -> Result:
    """Handle case where all keys are configured."""
    print("✓ All API keys are configured!")
    print("\nYou can still update any settings using:\n  claia set <key> <value>  or  claia get <key>\n")
    return Result(success=True, message="All API keys already configured")
  
  def _display_unset_keys(self, unset_keys: List[tuple]) -> None:
    """Display unset API keys."""
    print("The following API keys are not configured:\n")
    for i, (var_name, help_text) in enumerate(unset_keys, 1):
      print(f"  {i}. {help_text} ({var_name})")
    print(f"\n{'-' * 70}")
  
  def _display_config_methods(self) -> None:
    """Display available configuration methods."""
    print("\nYou can configure API keys in several ways:")
    print("  1. Interactively now (recommended for getting started)")
    print("  2. Using 'claia set' (e.g., claia set openai_api_token YOUR_KEY)")
    print("  3. Setting environment variables (e.g., CLAIA_OPENAI_API_TOKEN)")
    print("  4. Adding them to your .env file")
    print("  5. Editing settings.json in your files directory")
    
    print(f"\n{'-' * 70}")
  
  def _setup_cancelled(self) -> Result:
    """Handle cancelled setup."""
    print("\nSetup cancelled. You can run 'claia setup' again anytime.\n")
    return Result(success=True, message="Setup cancelled by user")
  
  def _configure_keys(self, unset_keys: List[tuple]) -> int:
    """Interactively configure each unset API key."""
    configured = 0
    
    for var_name, help_text in unset_keys:
      print(f"\n{help_text} ({var_name}):")
      print("  (Press Enter to skip)")
      
      try:
        value = input("  Value: ").strip()
        
        if value:
          setattr(self.settings, var_name, value)
          if var_name in self.settings._cli_sourced_settings:
            self.settings._cli_sourced_settings.remove(var_name)
          
          masked = "***" + value[-4:] if len(value) > 4 else "***"
          print(f"  ✓ Set {var_name} to {masked}")
          configured += 1
        else:
          print(f"  ⊘ Skipped {var_name}")
          
      except (KeyboardInterrupt, EOFError):
        print("\n\nSetup interrupted.")
        break
    
    return configured
