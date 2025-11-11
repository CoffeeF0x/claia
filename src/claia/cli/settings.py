"""
This module manages the configuration settings for the CLAI application.

It maintains a list of settings for the various libraries and modules used by CLAI,
and loads settings from various sources (environment variables and command-line arguments).
"""

# External dependencies
import os
import argparse
import json
from collections import defaultdict
from enum import Enum
from typing import Dict, Any, List, Tuple
from dotenv import load_dotenv

# Internal dependencies
from claia.lib.enums.logging import LogLevel, LogFormat



########################################################################
#                               ENUMS                                  #
########################################################################
class SettingCategory(Enum):
  """Categories for grouping configuration settings."""
  API = "API Credentials"
  ENDPOINT = "Endpoints & URLs"
  DIRECTORY = "Directories"
  MODEL = "Model Settings"
  PROMPT = "Prompt Settings"
  AGENT = "Agent Settings"
  VLLM = "VLLM Settings"
  APPLICATION = "Application Settings"
  INTEGRATION = "External Integrations"



########################################################################
#                               CONSTANTS                              #
########################################################################
DEFAULT_LOG_LEVEL  = LogLevel.WARNING
DEFAULT_LOG_FORMAT = LogFormat.STANDARD
DEFAULT_ENV_FILE = ".env"
DEFAULT_SETTINGS_FILE = "settings.json"
ENV_PREFIX = "CLAIA_"

# Format: (variable_name, default_value, externally_settable, category, help_text)
CONFIG_VARS: List[Tuple[str, Any, bool, SettingCategory, str]] = [
  # API Tokens
  ("openai_api_token",                  "",            True,  SettingCategory.API,          "OpenAI API Token"),
  ("anthropic_api_token",               "",            True,  SettingCategory.API,          "Anthropic API Token"),
  ("local_llm_api_token",               "",            True,  SettingCategory.API,          "LocalLLM API Token"),
  ("runpod_api_token",                  "",            True,  SettingCategory.API,          "RunPod API Token"),
  ("massed_compute_api_token",          "",            True,  SettingCategory.API,          "Massed Compute API Token"),
  ("openrouter_api_token",              "",            True,  SettingCategory.API,          "OpenRouter API Token"),
  ("huggingface_api_token",             "",            True,  SettingCategory.API,          "Hugging Face API Token"),
  ("cloudflare_api_token",              "",            True,  SettingCategory.API,          "Cloudflare API Token"),

  # URLs and Endpoints
  ("local_llm_base_url",                "",            True,  SettingCategory.ENDPOINT,     "LocalLLM Base URL"),

  # Directories
  ("files_directory",                   "storage",     True,  SettingCategory.DIRECTORY,    "Directory for generated, converted, or imported files"),
  ("models_directory",                  "models",      True,  SettingCategory.DIRECTORY,    "Directory for model files"),

  # Model Settings
  ("default_model",                     "",            True,  SettingCategory.MODEL,        "Default model name"),
  ("default_model_source",              "",            True,  SettingCategory.MODEL,        "Default model source"),

  # Prompt Settings
  ("default_prompt",                    "",            True,  SettingCategory.PROMPT,       "Default prompt name to use"),

  # Agent Settings
  ("default_agent",                     "",            True,  SettingCategory.AGENT,        "Default agent type"),

  # VLLM Settings
  ("vllm_zone",                         "",            True,  SettingCategory.VLLM,         "VLLM Zone"),
  ("vllm_email",                        "",            True,  SettingCategory.VLLM,         "VLLM Email"),
  ("vllm_subdomain",                    "",            True,  SettingCategory.VLLM,         "VLLM Subdomain"),
  ("vllm_eab_kid",                      "",            True,  SettingCategory.VLLM,         "VLLM EAB Kid"),
  ("vllm_eab_hmac_encoded",             "",            True,  SettingCategory.VLLM,         "VLLM EAB HMAC Encoded"),

  # Application Settings
  ("log_level",                         "",            True,  SettingCategory.APPLICATION,  "Logging level"),
  ("log_format",                        "",            True,  SettingCategory.APPLICATION,  "Logging format (simple, standard, detailed)"),
  ("log_file",                          "claia.log",   True,  SettingCategory.APPLICATION,  "Log file path (empty for console only)"),
  ("env_file",                          "",            True,  SettingCategory.APPLICATION,  "Path to .env file for configuration"),
  ("suppress_setup_notice",             False,         True,  SettingCategory.APPLICATION,  "Suppress API key setup notice on startup"),

  # Zammad Settings
  ("zammad_base_url",                   "",            True,  SettingCategory.INTEGRATION,  "Zammad Base URL"),
  ("zammad_api_token",                  "",            True,  SettingCategory.INTEGRATION,  "Zammad API Token"),
]



########################################################################
#                               CLASSES                                #
########################################################################
class Settings:
  """
  Stores and manages configuration settings for the CLAIA application.
  """

  def __init__(self):
    """Initialize configuration from environment variables and command line arguments."""
    self.loaded_local_models: Dict[str, Any] = {}

    self.prompt_store = []
    self.extra_args = []

    self.active_model = None
    self.active_model_source = None
    self.active_agent = None
    self.active_prompt = None
    self.active_conversation = None

    self.root_logger = None

    # Track which settings came from CLI (to avoid saving them to file)
    self._cli_sourced_settings = set()

    # Load configuration
    self._load_config()
    self.validate()
    
    # Save settings to file after loading (creates file if doesn't exist, updates if values changed)
    self._save_settings_to_file()


  def _load_config(self):
    """
    Load configuration from command line arguments, .env file, and environment variables
    Priority: Command line args > .env file > Environment variables > settings.json > Defaults
    """
    # Disable argparse's automatic -h/--help so our custom help handler can take over
    parser = argparse.ArgumentParser(description='CLAIA Settings', add_help=False)

    # Add arguments based on CONFIG_VARS, but only for externally settable ones
    for var_name, default, externally_settable, category, help_text in CONFIG_VARS:
      if externally_settable:
        cli_name = f"--{var_name.replace('_', '-')}"

        # Handle special case for boolean values
        if isinstance(default, bool):
          parser.add_argument(
            cli_name,
            type=lambda x: x.lower() == 'true',
            default=None,
            help=help_text)
        # Handle special case for integer values
        elif isinstance(default, int):
          parser.add_argument(
            cli_name,
            type=int,
            default=None,
            help=help_text)
        else:
          parser.add_argument(
            cli_name,
            default=None,
            help=help_text)

    # Parse known args, and store unknown args for later command processing
    args, unknown = parser.parse_known_args()
    self.extra_args = unknown

    # Track which settings were explicitly provided via CLI
    for var_name, default, externally_settable, category, help_text in CONFIG_VARS:
      if externally_settable:
        cli_name = var_name.lower()
        cli_value = getattr(args, cli_name, None)
        if cli_value is not None:
          self._cli_sourced_settings.add(var_name)

    # Load .env file if it exists (get env_file from args or use default)
    env_file = self._get_config_value("env_file", DEFAULT_ENV_FILE, args, True, {})
    if os.path.exists(env_file):
      load_dotenv(env_file, override=True)

    # Load settings from settings.json file first (lowest priority after defaults)
    # Need to get files_directory first to know where to look for settings.json
    files_dir = self._get_config_value("files_directory", "storage", args, True, {})
    json_settings = self._load_settings_from_file(files_dir)

    # Build config dictionary using helper function
    config_dict = {
      var_name: self._get_config_value(var_name, default, args, externally_settable, json_settings)
      for var_name, default, externally_settable, category, help_text in CONFIG_VARS
    }

    # Set all configuration values as instance attributes
    for key, value in config_dict.items():
      setattr(self, key, value)


  def _get_config_value(self, var_name: str, default: Any, args: argparse.Namespace, externally_settable: bool, json_settings: Dict[str, Any]) -> Any:
    """
    Helper function to get configuration value from CLI args, environment variables, or settings.json

    Args:
        var_name: The base variable name in snake_case
        default: Default value if no other source sets it
        args: Parsed command line arguments
        externally_settable: Whether this setting can be set from outside the application
        json_settings: Settings loaded from settings.json file
    
    Priority: CLI args > .env file > Environment variables > settings.json > Defaults
    """
    # If not externally settable, just return the default
    if not externally_settable:
      return default

    # Convert naming conventions
    env_name = var_name.upper()
    prefixed_env_name = f"{ENV_PREFIX}{var_name.upper()}"
    cli_name = var_name.lower()

    # Get value from CLI args (they're already parsed with defaults)
    value = getattr(args, cli_name, None)

    # If CLI value is None, try prefixed environment variable
    if value is None:
      value = os.getenv(prefixed_env_name)

    # If prefixed environment variable is None, try unprefixed environment variable
    if value is None:
      value = os.getenv(env_name)

    # If still None, try settings.json
    if value is None and var_name in json_settings:
      value = json_settings[var_name]

    # Strip quotes if present
    if value and isinstance(value, str) and value[0] == value[-1] and value[0] in ('"', "'"):
      value = value[1:-1]

    return value if value else default


  def validate(self) -> bool:
    """
    Validate the configuration settings.

    Returns:
      bool: Always returns True as API token validation is handled elsewhere.
    """
    try:
      LogLevel.from_string(self.log_level)
    except ValueError:
      if self.log_level:
        print(f"Invalid log level in environment variable. Using default: {DEFAULT_LOG_LEVEL.name}")
      self.log_level = DEFAULT_LOG_LEVEL.name

    try:
      LogFormat.from_string(self.log_format)
    except ValueError:
      if self.log_format:
        print(f"Invalid log format in environment variable. Using default: {DEFAULT_LOG_FORMAT.name}")
      self.log_format = DEFAULT_LOG_FORMAT.name

    return True


  def get_user_kwargs(self) -> Dict[str, Any]:
    """
    Get all user-supplied configuration values as kwargs.

    Returns:
        Dict[str, Any]: Dictionary of configuration values that can be passed as kwargs
    """
    kwargs = {}

    # Iterate through CONFIG_VARS to get all user-configurable settings
    for var_name, default, externally_settable, category, help_text in CONFIG_VARS:
      if externally_settable:
        kwargs[var_name] = getattr(self, var_name, default)

    return kwargs


  def _load_settings_from_file(self, files_directory: str) -> Dict[str, Any]:
    """
    Load settings from settings.json file in the files directory.

    Args:
        files_directory: The directory where settings.json should be located

    Returns:
        Dict[str, Any]: Dictionary of settings loaded from file, or empty dict if file doesn't exist
    """
    settings_path = os.path.join(files_directory, DEFAULT_SETTINGS_FILE)
    
    if not os.path.exists(settings_path):
      return {}
    
    try:
      with open(settings_path, 'r') as f:
        return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
      print(f"Warning: Could not load settings from {settings_path}: {e}")
      return {}


  def _save_settings_to_file(self) -> None:
    """
    Save current settings to settings.json file in the files directory.
    Only saves externally settable configuration values.
    Excludes settings that were provided via CLI arguments (they should not persist).
    Creates the file if it doesn't exist, updates if values have changed.
    """
    settings_path = os.path.join(self.files_directory, DEFAULT_SETTINGS_FILE)
    
    # Ensure the directory exists
    os.makedirs(self.files_directory, exist_ok=True)
    
    # Load existing settings to preserve CLI-sourced values that were previously saved
    existing_settings = {}
    if os.path.exists(settings_path):
      try:
        with open(settings_path, 'r') as f:
          existing_settings = json.load(f)
      except (json.JSONDecodeError, IOError):
        pass  # If we can't read it, we'll overwrite it
    
    # Build dictionary of current settings (excluding CLI-sourced ones)
    current_settings = {}
    for var_name, default, externally_settable, category, help_text in CONFIG_VARS:
      if externally_settable:
        # If this setting came from CLI, preserve the existing file value (if any)
        if var_name in self._cli_sourced_settings:
          if var_name in existing_settings:
            current_settings[var_name] = existing_settings[var_name]
          # Otherwise skip it - don't save CLI values to file
        else:
          # Save non-CLI settings normally
          current_settings[var_name] = getattr(self, var_name, default)
    
    # Only write if settings have changed or file doesn't exist
    if current_settings != existing_settings:
      try:
        with open(settings_path, 'w') as f:
          json.dump(current_settings, f, indent=2)
      except IOError as e:
        print(f"Warning: Could not save settings to {settings_path}: {e}")


  def get_unset_api_keys(self) -> List[Tuple[str, str]]:
    """
    Get a list of API tokens that are not set (empty or default value).

    Returns:
        List of tuples containing (var_name, help_text) for unset API tokens
    """
    unset_keys = []
    
    for var_name, default, externally_settable, category, help_text in CONFIG_VARS:
      # Only check API tokens
      if category == SettingCategory.API and externally_settable:
        value = getattr(self, var_name, default)
        if not value or value == default:
          unset_keys.append((var_name, help_text))
    
    return unset_keys


  def get_setting_info(self, setting_name: str) -> Tuple[Any, Any, str, SettingCategory]:
    """
    Get information about a specific setting.

    Args:
        setting_name: The setting name to look up

    Returns:
        Tuple of (current_value, default_value, help_text, category)
        Returns (None, None, "", None) if setting not found or not externally settable
    """
    setting_name = setting_name.lower().replace('-', '_')
    
    for var_name, default, externally_settable, category, help_text in CONFIG_VARS:
      if var_name == setting_name and externally_settable:
        current_value = getattr(self, var_name, default)
        return (current_value, default, help_text, category)
    
    return (None, None, "", None)


  def get_all_settings_info(self) -> Dict[SettingCategory, List[Tuple[str, Any, str]]]:
    """
    Get all externally settable settings grouped by category.

    Returns:
        Dictionary mapping category to list of (var_name, current_value, help_text) tuples
    """
    categorized = defaultdict(list)
    
    for var_name, default, externally_settable, category, help_text in CONFIG_VARS:
      if externally_settable:
        value = getattr(self, var_name, default)
        # Mask sensitive values
        display_value = self._mask_sensitive_value(var_name, value)
        categorized[category].append((var_name, display_value, help_text))
    
    return categorized


  def is_valid_setting(self, setting_name: str) -> bool:
    """
    Check if a setting name is valid and externally settable.

    Args:
        setting_name: The setting name to check

    Returns:
        True if the setting is valid and externally settable, False otherwise
    """
    setting_name = setting_name.lower().replace('-', '_')
    
    for var_name, _, externally_settable, _, _ in CONFIG_VARS:
      if var_name == setting_name and externally_settable:
        return True
    
    return False


  def update_setting(self, setting_name: str, value: Any) -> Tuple[bool, str, Any]:
    """
    Update a setting with type conversion and validation.

    Args:
        setting_name: The setting name to update
        value: The new value (will be type-converted as needed)

    Returns:
        Tuple of (success, message, old_value)
    """
    setting_name = setting_name.lower().replace('-', '_')
    
    # Find the setting in CONFIG_VARS
    setting_found = False
    default_value = None
    
    for var_name, default, externally_settable, category, help_text in CONFIG_VARS:
      if var_name == setting_name and externally_settable:
        setting_found = True
        default_value = default
        break
    
    if not setting_found:
      return (False, f"Unknown setting: {setting_name}", None)
    
    # Type conversion
    try:
      if isinstance(default_value, bool):
        value = value.lower() in ('true', '1', 'yes', 'on') if isinstance(value, str) else bool(value)
      elif isinstance(default_value, int):
        value = int(value)
      # Otherwise keep as string
    except (ValueError, AttributeError) as e:
      return (False, f"Invalid value for {setting_name}: {value}", None)
    
    # Get old value and update
    old_value = getattr(self, setting_name, None)
    setattr(self, setting_name, value)
    
    # Remove from CLI sourced settings if present (so it will be saved to file)
    if setting_name in self._cli_sourced_settings:
      self._cli_sourced_settings.remove(setting_name)
    
    # Save to file
    try:
      self._save_settings_to_file()
      return (True, f"Setting '{setting_name}' updated successfully", old_value)
    except Exception as e:
      # Revert on failure
      setattr(self, setting_name, old_value)
      return (False, f"Failed to save setting: {str(e)}", old_value)


  def _mask_sensitive_value(self, var_name: str, value: Any) -> Any:
    """
    Mask sensitive values (tokens, passwords) for display.

    Args:
        var_name: The variable name
        value: The value to potentially mask

    Returns:
        Masked value if sensitive, otherwise original value
    """
    if 'token' in var_name.lower() or 'password' in var_name.lower():
      if value and value != "":
        return "***" + value[-4:] if len(str(value)) > 4 else "***"
    return value
