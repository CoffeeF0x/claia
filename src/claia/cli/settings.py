"""
This module manages the configuration settings for the CLAI application.

It maintains a list of settings for the various libraries and modules used by CLAI,
and loads settings from various sources (environment variables and command-line arguments).
"""

# External dependencies
import os
import argparse
from typing import Dict, Any, List, Tuple
from dotenv import load_dotenv

# Internal dependencies
from claia.common.enums.logging import LogLevel, LogFormat



########################################################################
#                               CONSTANTS                              #
########################################################################
DEFAULT_LOG_LEVEL  = LogLevel.WARNING
DEFAULT_LOG_FORMAT = LogFormat.STANDARD
DEFAULT_ENV_FILE = ".env"
ENV_PREFIX = "CLAIA_"

# Format: (variable_name, default_value, externally_settable, help_text)
CONFIG_VARS: List[Tuple[str, Any, bool, str]] = [
  # API Tokens
  ("openai_api_token",                  "",            True,  "OpenAI API Token"),
  ("anthropic_api_token",               "",            True,  "Anthropic API Token"),
  ("local_llm_api_token",               "",            True,  "LocalLLM API Token"),
  ("runpod_api_token",                  "",            True,  "RunPod API Token"),
  ("massed_compute_api_token",          "",            True,  "Massed Compute API Token"),
  ("openrouter_api_token",              "",            True,  "OpenRouter API Token"),
  ("huggingface_api_token",             "",            True,  "Hugging Face API Token"),
  ("cloudflare_api_token",              "",            True,  "Cloudflare API Token"),

  # URLs and Endpoints
  ("local_llm_base_url",                "",            True,  "LocalLLM Base URL"),

  # Directories
  ("files_directory",                   "storage",     True,  "Directory for generated, converted, or imported files"),
  ("modules_directory",                 "modules",     True,  "Directory for claia modules"),
  ("models_directory",                  "models",      True,  "Directory for model files"),

  # Model Settings
  ("default_model",                     "",            True,  "Default model name"),
  ("default_model_source",              "",            True,  "Default model source"),

  # Prompt Settings
  ("default_prompt",                    "",            True,  "Default prompt name to use"),

  # Agent Settings
  ("default_agent",                     "",            True,  "Default agent type"),

  # VLLM Settings
  ("vllm_zone",                         "",            True,  "VLLM Zone"),
  ("vllm_email",                        "",            True,  "VLLM Email"),
  ("vllm_subdomain",                    "",            True,  "VLLM Subdomain"),
  ("vllm_eab_kid",                      "",            True,  "VLLM EAB Kid"),
  ("vllm_eab_hmac_encoded",             "",            True,  "VLLM EAB HMAC Encoded"),

  # Application Settings
  ("log_level",                         "",            True,  "Logging level"),
  ("log_format",                        "",            True,  "Logging format (simple, standard, detailed)"),
  ("log_file",                          "claia.log",   True,  "Log file path (empty for console only)"),
  ("env_file",                          "",            True,  "Path to .env file for configuration"),
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
    self.command_modules = []
    self.function_modules = []
    self.function_definitions = []
    self.extra_args = []

    self.active_model = None
    self.active_model_source = None
    self.active_agent = None
    self.active_prompt = None
    self.active_conversation = None

    self.root_logger = None

    # Load configuration
    self._load_config()
    self.validate()


  def _load_config(self):
    """
    Load configuration from command line arguments, .env file, and environment variables
    Priority: Command line args > .env file > Environment variables > Defaults
    """
    parser = argparse.ArgumentParser(description='CLAIA Settings')

    # Add arguments based on CONFIG_VARS, but only for externally settable ones
    for var_name, default, externally_settable, help_text in CONFIG_VARS:
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

    # Load .env file if it exists (get env_file from args or use default)
    env_file = self._get_config_value("env_file", DEFAULT_ENV_FILE, args, True)
    if os.path.exists(env_file):
      load_dotenv(env_file, override=True)

    # Build config dictionary using helper function
    config_dict = {
      var_name: self._get_config_value(var_name, default, args, externally_settable)
      for var_name, default, externally_settable, _ in CONFIG_VARS
    }

    # Set all configuration values as instance attributes
    for key, value in config_dict.items():
      setattr(self, key, value)


  def _get_config_value(self, var_name: str, default: Any, args: argparse.Namespace, externally_settable: bool) -> Any:
    """
    Helper function to get configuration value from CLI args or environment variables

    Args:
        var_name: The base variable name in snake_case
        default: Default value if no other source sets it
        args: Parsed command line arguments
        externally_settable: Whether this setting can be set from outside the application
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


  def has_command_modules(self) -> bool:
    """
    Check if there are any available command modules.

    Returns:
      bool: True if there are available command modules, False otherwise
    """
    return len(self.command_modules) > 0


  def has_function_modules(self) -> bool:
    """
    Check if there are any available function modules.

    Returns:
      bool: True if there are available function modules, False otherwise
    """
    return len(self.function_modules) > 0


  def set_function_definitions(self, function_definitions: List[Dict[str, Any]]) -> None:
    """
    Set the function definitions for function calling.

    Args:
        function_definitions: List of function definitions
    """
    self.function_definitions = function_definitions


  def get_user_kwargs(self) -> Dict[str, Any]:
    """
    Get all user-supplied configuration values as kwargs.

    Returns:
        Dict[str, Any]: Dictionary of configuration values that can be passed as kwargs
    """
    kwargs = {}

    # Iterate through CONFIG_VARS to get all user-configurable settings
    for var_name, default, externally_settable, _ in CONFIG_VARS:
      if externally_settable:
        value = getattr(self, var_name, default)
        # Only include values that are not empty/default
        if value and value != default:
          kwargs[var_name] = value

    return kwargs
