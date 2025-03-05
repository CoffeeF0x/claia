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
from file import LLMPromptStore, ChatHistory



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
  ("chat_history_directory",            "history",                     True,  "Directory for chat histories"),
  ("modules_directory",                 "modules",                     True,  "Directory for modules"),

  # Model Settings
  ("active_model",                      "gpt-4",                       True,  "Active model name"),
  ("active_model_source",               "openai",                      True,  "Active model source"),

  # VLLM Settings
  ("vllm_zone",                         "",                            True,  "VLLM Zone"),
  ("vllm_email",                        "",                            True,  "VLLM Email"),
  ("vllm_subdomain",                    "",                            True,  "VLLM Subdomain"),

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
    chat_history_directory (str): Directory to store chat histories.
    active_prompt (Optional[LLMPromptStore]): Currently active system prompt.
    active_chat (Optional[ChatHistory]): Currently active chat history.
    active_model (str): Currently active model name.
    log_level (str): Logging level.
    openrouter_api_token (str): API token for OpenRouter.
    active_model_source (Optional[str]): Currently active model source (e.g. "anthropic", "openai", etc).
    huggingface_api_token (str): API token for Hugging Face.
    vllm_zone (str): Zone for VLLM.
    vllm_email (str): Email for VLLM.
    vllm_subdomain (str): Subdomain for VLLM.
    min_function_calls (int): Minimum number of function calls to process.
    max_function_calls (int): Maximum number of function calls to process.
    default_prompt_name (str): Default prompt name to use.
  """

  def __init__(self):
    """Initialize configuration from environment variables and command line arguments."""
    self.loaded_local_models: Dict[str, Any] = {}
    self.prompt_store = []
    self.active_prompt = None
    self.active_chat = None
    self.command_modules = []
    self.function_modules = []

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
    self.active_chat = ChatHistory(self.chat_history_directory, "New Conversation", [])

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

  def load_all_prompts(self) -> list[LLMPromptStore]:
    # Load default prompts
    for prompt in DEFAULT_PROMPTS:
      if not self.prompt_exists(prompt['name']):
        self.prompt_store.append(LLMPromptStore(self.prompt_store_directory, prompt['name'], prompt['title'], prompt['prompt'], prompt['description']))
      else:
        pass
        # TODO: log error, prompt name already exists

    # Load prompts from the directory
    # TODO: Update to use the file get function, and maybe add a get all stores type function that returns a list of LLMPromptStore objects
    files = LLMPromptStore.list_files(self.prompt_store_directory)
    for filename in files:
      full_path = os.path.join(self.prompt_store_directory, filename)
      with open(full_path, 'r') as file:
        data = json.load(file)
        if not self.prompt_exists(data['name']):
          self.prompt_store.append(LLMPromptStore(self.prompt_store_directory, data['name'], data['title'], data['prompt'], data['description']))
        else:
          pass
          # TODO: log error, prompt name already exists

  def prompt_exists(self, name: str) -> bool:
    formatted_name = LLMPromptStore.validate_and_format_name(name)
    return any(prompt.name == formatted_name for prompt in self.prompt_store)

  def get_prompt(self, name: str) -> LLMPromptStore:
    return next((p for p in self.prompt_store if p.name == name), None)

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

# Usage example
if __name__ == "__main__":
  settings = Settings()
  if settings.validate():
    print("Settings loaded successfully")
  else:
    print("Error loading settings")
