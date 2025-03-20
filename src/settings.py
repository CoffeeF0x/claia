"""
This module manages the configuration settings for the CLAI application.

It maintains a list of settings for the various libraries and modules used by CLAI,
and loads settings from various sources (environment variables and command-line arguments).
"""

# External dependencies
import os
import json
import argparse
import logging
from typing import Dict, Any, List, Tuple, Optional
import logging

# Internal dependencies
from conversations import Conversation
from conversations.prompts import Prompt
from conversations.base import BaseFile
from enums import MessageRole



########################################################################
#                               CONSTANTS                              #
########################################################################
# Logging levels
LOG_LEVELS = {
  "debug":    logging.DEBUG,
  "info":     logging.INFO,
  "warning":  logging.WARNING,
  "error":    logging.ERROR,
  "critical": logging.CRITICAL
}

# Logging formats
LOG_FORMATS = {
  "simple": "%(levelname)s: %(message)s",
  "standard": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
  "detailed": "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
}

# Function calling prompt template
FUNCTION_CALLING_PROMPT = """
You are an AI assistant capable of calling functions. Here are the available functions:

{function_definitions}

When you need to call a function, use the following format:
{function_format}

You can call multiple functions in a single response if needed. Each function call will be replaced with its result.
Incorporate the function call(s) into your response where necessary.
"""

# Default prompts
DEFAULT_PROMPTS = [
  {
    "name": "default",
    "title": "Default Assistant",
    "prompt": "You are a helpful assistant, ready to aid the user with any task or question they might have.",
    "description": "A general-purpose assistant for various tasks."
  },
  {
    "name": "poet",
    "title": "Poet",
    "prompt": "You are a poetic assistant, skilled in explaining complex programming concepts with creative flair.",
    "description": "A default assistant with a poetic twist."
  },
  {
    "name": "writer",
    "title": "Writer",
    "prompt": "You are a brilliant writer, always adding events and details that give life to the story, making sure to show and not tell about environments, characters, and actions.",
    "description": "An assistant for creative writing tasks."
  },
  {
    "name": "also-writer",
    "title": "Also Writer",
    "prompt": "You are a creative writer, skilled in crafting engaging narratives and vivid descriptions. Help the user with their writing tasks, offering suggestions for plot, character development, and prose.",
    "description": "An assistant for creative writing tasks."
  },
  {
    "name": "programmer",
    "title": "Programmer",
    "prompt": "You are a skilled programmer, proficient in multiple programming languages. You provide clear explanations and code examples to help with various programming tasks.",
    "description": "An assistant for programming and coding tasks."
  },
  {
    "name": "analyst",
    "title": "Analyst",
    "prompt": "You are a data analyst with expertise in statistics and data visualization. You help interpret data, suggest analysis methods, and explain complex analytical concepts.",
    "description": "An assistant for data analysis and interpretation."
  },
  {
    "name": "functions",
    "title": "Function Calling Assistant",
    "prompt": FUNCTION_CALLING_PROMPT,
    "description": "An assistant capable of calling functions."
  }
]

# Format: (variable_name, default_value, externally_settable, help_text)
CONFIG_VARS: List[Tuple[str, Any, bool, str]] = [
  # API Tokens
  ("openai_api_token",                  "",                            True,  "OpenAI API Token"),
  ("anthropic_api_token",               "",                            True,  "Anthropic API Token"),
  ("local_llm_api_token",               "",                            True,  "LocalLLM API Token"),
  ("runpod_api_token",                  "",                            True,  "RunPod API Token"),
  ("massed_compute_api_token",          "",                            True,  "Massed Compute API Token"),
  ("openrouter_api_token",              "",                            True,  "OpenRouter API Token"),
  ("huggingface_api_token",             "",                            True,  "Hugging Face API Token"),
  ("cloudflare_api_token",              "",                            True,  "Cloudflare API Token"),

  # URLs and Endpoints
  ("local_llm_base_url",                "",                            True,  "LocalLLM Base URL"),

  # Directories
  ("model_directory",                   "models",                      True,  "Directory for model files"),
  ("prompt_directory",                  "prompts",                     True,  "Directory for prompt stores"),
  ("conversation_directory",            "conversations",               True,  "Directory for conversations"),
  ("modules_directory",                 "modules",                     True,  "Directory for modules"),
  ("artifacts_directory",               "artifacts",                   True,  "Directory for persistent artifacts"),
  ("conversation_files_directory",      "files",                       True,  "Directory for conversation files"),
  ("temp_directory",                    "temp",                        True,  "Directory for temporary files"),

  # Model Settings
  ("active_model",                      "qwq-32b",                     True,  "Active model name"),
  ("active_model_source",               "",                            True,  "Active model source"),

  # Agent Settings
  ("active_agent",                      "simple",                      True,  "Active agent type"),

  # VLLM Settings
  ("vllm_zone",                         "",                            True,  "VLLM Zone"),
  ("vllm_email",                        "",                            True,  "VLLM Email"),
  ("vllm_subdomain",                    "",                            True,  "VLLM Subdomain"),
  ("vllm_eab_kid",                      "",                            True,  "VLLM EAB Kid"),
  ("vllm_eab_hmac_encoded",             "",                            True,  "VLLM EAB HMAC Encoded"),

  # Prompt Settings
  ("default_prompt_name",               "default",                     True,  "Default prompt name to use"),

  # Application Settings
  ("log_level",                         "warning",                     True,  "Logging level"),
  ("log_format",                        "standard",                    True,  "Logging format (simple, standard, detailed)"),
  ("log_file",                          "claia.log",                   True,  "Log file path (empty for console only)"),
  ("min_function_calls",                5,                             True,  "Minimum number of function calls to process"),
  ("max_function_calls",                10,                            True,  "Maximum number of function calls to process"),
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
    self.active_prompt = None
    self.active_conversation = None
    self.command_modules = []
    self.function_modules = []
    self.function_definitions = []
    self.root_logger = None

    # Load configuration
    self._load_config()

    # Ensure all required directories exist
    self._ensure_directories_exist()

    # Initialize after loading config
    self.load_all_prompts()
    self.active_prompt = self.get_prompt(self.default_prompt_name)

    # Initialize with a new conversation
    if self.active_prompt:
      self.active_conversation = Conversation(
        base_directory=self.conversation_directory,
        files_directory=self.conversation_files_directory,
        title="New Conversation",
        system_prompt=self.active_prompt.prompt_text
      )
    else:
      self.active_conversation = Conversation(
        base_directory=self.conversation_directory,
        files_directory=self.conversation_files_directory,
        title="New Conversation"
      )

  def _load_config(self):
    """
    Load configuration from environment variables and command line arguments.
    Command line arguments take precedence over environment variables.
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

    args = parser.parse_args()

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
    Helper function to get configuration value from either CLI args or environment variables.
    CLI args take precedence over environment variables.

    Args:
        var_name: The base variable name in snake_case
        default: Default value if neither CLI arg nor env var is set
        args: Parsed command line arguments
        externally_settable: Whether this setting can be set from outside the application
    """
    # If not externally settable, just return the default
    if not externally_settable:
      return default

    # Convert naming conventions
    env_name = var_name.upper()
    cli_name = var_name.replace('_', '-')

    # Get value from CLI args (they're already parsed with defaults)
    cli_value = getattr(args, var_name, None)

    # If CLI value is None, try environment variable
    if cli_value is None:
      env_value = os.getenv(env_name)
      if env_value is not None:
        # Strip quotes if present
        if env_value and env_value[0] == env_value[-1] and env_value[0] in ('"', "'"):
          env_value = env_value[1:-1]
        return env_value
      return default

    return cli_value

  def configure_logging(self) -> None:
    """
    Configure the logging system based on the current settings.
    This should be called early in the application startup.
    """
    # Validate log level
    if self.log_level not in LOG_LEVELS:
      print(f"Invalid log level: {self.log_level}. Using default: error")
      self.log_level = "error"

    # Validate log format
    if self.log_format not in LOG_FORMATS:
      print(f"Invalid log format: {self.log_format}. Using default: standard")
      self.log_format = "standard"

    # Get the numeric log level and format string
    log_level = LOG_LEVELS[self.log_level]
    log_format = LOG_FORMATS[self.log_format]

    # Create a formatter
    formatter = logging.Formatter(log_format)

    # Configure the root logger
    self.root_logger = logging.getLogger()
    self.root_logger.setLevel(log_level)

    # Remove any existing handlers
    for handler in self.root_logger.handlers[:]:
      self.root_logger.removeHandler(handler)

    # Always add a console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    self.root_logger.addHandler(console_handler)

    # Add a file handler if a log file is specified
    if self.log_file:
      try:
        # Ensure the directory exists
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
          os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.FileHandler(self.log_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        self.root_logger.addHandler(file_handler)

        # Log that we've started logging to a file
        self.root_logger.info(f"Logging to file: {self.log_file}")
      except Exception as e:
        self.root_logger.error(f"Failed to set up file logging to {self.log_file}: {e}")

    # Log the configuration
    self.root_logger.debug(f"Logging configured with level={self.log_level}, format={self.log_format}")

  def load_all_prompts(self) -> list[Prompt]:
    """
    Load all prompts from the default prompts and the prompt store directory.

    Returns:
        list[Prompt]: A list of all loaded prompts
    """
    # Ensure the prompt store directory exists
    BaseFile.ensure_directory(os.path.join(self.prompt_directory))

    # Get list of existing prompt names
    existing_prompt_names = Prompt.get_prompt_names(self.prompt_directory)

    # Create any default prompts that don't exist yet
    for prompt_data in DEFAULT_PROMPTS:
      formatted_name = Prompt.validate_and_format_name(prompt_data['name'])
      if formatted_name not in existing_prompt_names:
        # Create and save the prompt
        prompt = Prompt(
          base_directory=self.prompt_directory,
          name=prompt_data['name'],
          title=prompt_data['title'],
          prompt=prompt_data['prompt'],
          description=prompt_data['description']
        )
        prompt.save()

    # Load all prompts from the directory
    self.prompt_store = []
    prompt_names = Prompt.get_prompt_names(self.prompt_directory)
    for name in prompt_names:
      prompt = Prompt.load(name, self.prompt_directory)
      if prompt:
        self.prompt_store.append(prompt)

    return self.prompt_store

  def get_prompt(self, name: str) -> Optional[Prompt]:
    """
    Get a prompt by name.

    Args:
        name: The name of the prompt to get

    Returns:
        Optional[Prompt]: The prompt with the given name, or None if not found
    """
    formatted_name = Prompt.validate_and_format_name(name)
    return next((p for p in self.prompt_store if p.name == formatted_name), None)

  def validate(self) -> bool:
    """
    Validate the configuration settings.

    Returns:
      bool: Always returns True as API token validation is handled elsewhere.
    """
    if self.log_level not in LOG_LEVELS:
      print(f"Invalid log level in environment variable. Using default: {self.log_level}")
      self.log_level = "error"

    if self.log_format not in LOG_FORMATS:
      print(f"Invalid log format in environment variable. Using default: {self.log_format}")
      self.log_format = "standard"

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

  def apply_function_definitions_to_active_prompt(self) -> None:
    """
    Apply the current function definitions to the active prompt.
    This should be called before using the active prompt to ensure it has the latest function definitions.
    """
    if self.active_prompt and self.active_prompt.name == "functions":
      self.active_prompt.load_function_definitions(self.function_definitions)
      self.root_logger.info(f"Applied {len(self.function_definitions)} function definitions to active prompt")
    elif self.active_prompt:
      # For non-function prompts, we still load the definitions in case they're needed
      self.active_prompt.load_function_definitions(self.function_definitions)

  def _ensure_directories_exist(self):
    """Ensure all required directories exist."""
    directories = [
      self.model_directory,
      self.prompt_directory,
      self.conversation_directory,
      self.modules_directory,
      self.artifacts_directory,
      self.conversation_files_directory,
      self.temp_directory
    ]

    for directory in directories:
      if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        if self.root_logger:
          self.root_logger.debug(f"Created directory: {directory}")

# Usage example
if __name__ == "__main__":
  settings = Settings()
  if settings.validate():
    settings.configure_logging()
    print("Settings loaded successfully")
  else:
    print("Error loading settings")
