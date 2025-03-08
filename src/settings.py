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

# Internal dependencies
from conversations import Conversation, MessageRole
from conversations.prompts import Prompt
from conversations.base import BaseFile



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
  ("prompt_store_directory",            "prompts",                     True,  "Directory for prompt stores"),
  ("conversation_directory",            "conversations",               True,  "Directory for conversations"),
  ("modules_directory",                 "modules",                     True,  "Directory for modules"),
  ("artifacts_directory",               "artifacts",                   True,  "Directory for persistent artifacts"),
  ("conversation_files_directory",      "files",                       True,  "Directory for conversation files"),
  ("temp_directory",                    "temp",                        True,  "Directory for temporary files"),

  # Model Settings
  ("active_model",                      "qwq-32b",                     True,  "Active model name"),
  ("active_model_source",               "",                            True,  "Active model source"),

  # VLLM Settings
  ("vllm_zone",                         "",                            True,  "VLLM Zone"),
  ("vllm_email",                        "",                            True,  "VLLM Email"),
  ("vllm_subdomain",                    "",                            True,  "VLLM Subdomain"),
  ("vllm_eab_kid",                      "",                            True,  "VLLM EAB Kid"),
  ("vllm_eab_hmac_encoded",             "",                            True,  "VLLM EAB HMAC Encoded"),

  # Prompt Settings
  ("default_prompt_name",               "default",                     True,  "Default prompt name to use"),

  # Application Settings
  ("log_level",                         "error",                       True,  "Logging level"),
  ("min_function_calls",                5,                             True,  "Minimum number of function calls to process"),
  ("max_function_calls",                10,                            True,  "Maximum number of function calls to process"),
]



########################################################################
#                               CLASSES                                #
########################################################################
class Settings:
  """
  Stores and manages configuration settings for the CLAI application.

  Attributes:
    openai_api_token (str): API token for OpenAI.
    anthropic_api_token (str): API token for Anthropic.
    local_llm_api_token (str): API token for local LLM.
    runpod_api_token (str): API token for RunPod.
    local_llm_base_url (str): Base URL for local LLM.
    massed_compute_api_token (str): API token for Massed Compute.
    prompt_store_directory (str): Directory to store LLM prompt stores.
    conversation_directory (str): Directory to store conversation histories.
    active_prompt (Optional[Prompt]): Currently active system prompt.
    active_conversation (Optional[Conversation]): Currently active conversation.
    active_model (str): Currently active model name.
    log_level (str): Logging level.
    openrouter_api_token (str): API token for OpenRouter.
    active_model_source (Optional[str]): Currently active model source (e.g. "anthropic", "openai", etc).
    huggingface_api_token (str): API token for Hugging Face.
    vllm_zone (str): Zone for VLLM.
    vllm_email (str): Email for VLLM.
    vllm_subdomain (str): Subdomain for VLLM.
    vllm_eab_kid (str): EAB Kid for ZeroSSL for VLLM.
    vllm_eab_hmac_encoded (str): EAB HMAC Encoded for ZeroSSL for VLLM.
    min_function_calls (int): Minimum number of function calls to process.
    max_function_calls (int): Maximum number of function calls to process.
    default_prompt_name (str): Default prompt name to use.
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

    # Boolean flags for API key availability
    self.has_openai_api_token = False
    self.has_anthropic_api_token = False
    self.has_local_llm_api_token = False
    self.has_runpod_api_token = False
    self.has_massed_compute_api_token = False
    self.has_openrouter_api_token = False
    self.has_huggingface_api_token = False
    self.has_cloudflare_api_token = False

    # Load configuration
    self._load_config()

    # Initialize after loading config
    self.load_all_prompts()
    self.active_prompt = self.get_prompt(self.default_prompt_name)

    # Initialize with a new conversation
    if self.active_prompt:
      self.active_conversation = Conversation(
        conversation_directory=self.conversation_directory,
        artifacts_directory=self.artifacts_directory,
        title="New Conversation",
        system_prompt=self.active_prompt,
        files_subdirectory=self.conversation_files_directory
      )
    else:
      self.active_conversation = Conversation(
        conversation_directory=self.conversation_directory,
        artifacts_directory=self.artifacts_directory,
        title="New Conversation",
        files_subdirectory=self.conversation_files_directory
      )

  def _load_config(self):
    """
    Load configuration from environment variables and command line arguments.
    Command line arguments take precedence over environment variables.
    """
    parser = argparse.ArgumentParser(description='CLAI Settings')

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

    # Set API token flags
    self.has_openai_api_token = bool(self.openai_api_token)
    self.has_anthropic_api_token = bool(self.anthropic_api_token)
    self.has_local_llm_api_token = bool(self.local_llm_api_token)
    self.has_runpod_api_token = bool(self.runpod_api_token)
    self.has_massed_compute_api_token = bool(self.massed_compute_api_token)
    self.has_openrouter_api_token = bool(self.openrouter_api_token)
    self.has_huggingface_api_token = bool(self.huggingface_api_token)
    self.has_cloudflare_api_token = bool(self.cloudflare_api_token)

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

  def load_all_prompts(self) -> list[Prompt]:
    """
    Load all prompts from the default prompts and the prompt store directory.

    Returns:
        list[Prompt]: A list of all loaded prompts
    """

    # Get list of existing prompt names
    existing_prompt_names = Prompt.get_prompt_names(self.prompt_store_directory)

    # Create any default prompts that don't exist yet
    for prompt_data in DEFAULT_PROMPTS:
      formatted_name = Prompt.validate_and_format_name(prompt_data['name'])
      if formatted_name not in existing_prompt_names:
        # Create and save the prompt
        prompt = Prompt(
          self.prompt_store_directory,
          prompt_data['name'],
          prompt_data['title'],
          prompt_data['prompt'],
          prompt_data['description']
        )
        prompt.save()

    # Load all prompts from the directory
    self.prompt_store = Prompt.load_prompts_from_directory(self.prompt_store_directory)

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
      bool: True if at least one API token is present, False otherwise.
    """
    if self.log_level not in LOG_LEVELS:
      print(f"Invalid log level in environment variable. Using default: {self.log_level}")
      self.log_level = "error"

    api_tokens_present = (
      self.has_openai_api_token or
      self.has_anthropic_api_token or
      self.has_local_llm_api_token or
      self.has_runpod_api_token or
      self.has_massed_compute_api_token or
      self.has_openrouter_api_token or
      self.has_huggingface_api_token or
      self.has_cloudflare_api_token
    )

    if not api_tokens_present:
      print("No API tokens found. At least one API token is required.")

    return api_tokens_present

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
      print(f"Applied {len(self.function_definitions)} function definitions to active prompt")
    elif self.active_prompt:
      # For non-function prompts, we still load the definitions in case they're needed
      self.active_prompt.load_function_definitions(self.function_definitions)

# Usage example
if __name__ == "__main__":
  settings = Settings()
  if settings.validate():
    print("Settings loaded successfully")
  else:
    print("Error loading settings")
