"""
This module manages the configuration settings for the CLAI application.

It provides a Settings class to store settings and a SettingsFactory to create
and load settings from various sources (environment variables and command-line arguments).
"""

import os
import json
import argparse
import logging
from typing import Dict, Any
from file import LLMPromptStore, ChatHistory
from functions.definitions import prompt as function_calling_prompt

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
    zammad_api_token (str): API token for Zammad.
    zammad_base_url (str): Base URL for Zammad API.
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
  """

  LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL
  }

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

  DEFAULT_PROMPT_NAME = "default"
  DEFAULT_MODEL = "qwen2.5-72b-instruct" # "claude-3-5-sonnet-20240620"
  DEFAULT_MODEL_SOURCE = "vllm" # None
  DEFAULT_LOG_LEVEL = "error"
  DEFAULT_MODEL_DIRECTORY = "models"
  DEFAULT_PROMPT_DIRECTORY = "prompts"
  DEFAULT_CHAT_DIRECTORY = "history"
  FUNCTION_CALLING_PROMPT_NAME = "functions"

  def __init__(self):
    # print("Initializing Settings")
    self.openai_api_token: str = ""
    self.anthropic_api_token: str = ""
    self.local_llm_api_token: str = ""
    self.runpod_api_token: str = ""
    self.local_llm_base_url: str = ""
    self.massed_compute_api_token: str = ""
    self.zammad_api_token: str = ""
    self.zammad_base_url: str = ""
    self.model_directory: str = self.DEFAULT_MODEL_DIRECTORY
    self.prompt_store_directory: str = self.DEFAULT_PROMPT_DIRECTORY
    self.chat_history_directory: str = self.DEFAULT_CHAT_DIRECTORY
    self.loaded_local_models: Dict[str, Any] = {}
    self.prompt_store = []
    self.load_all_prompts()
    self.active_prompt = self.get_prompt(self.DEFAULT_PROMPT_NAME)
    self.active_chat: ChatHistory = ChatHistory(self.chat_history_directory, "New Conversation", [])
    self.active_model: str = self.DEFAULT_MODEL
    self.active_model_source: str = self.DEFAULT_MODEL_SOURCE
    self.log_level: str = self.DEFAULT_LOG_LEVEL
    self.openrouter_api_token: str = ""
    self.huggingface_api_token: str = ""
    self.cloudflare_api_token: str = ""
    
    # VLLM specific settings
    self.vllm_zone: str = None
    self.vllm_email: str = None
    self.vllm_subdomain: str = None
    
    # Boolean flags for API key availability
    self.has_openai_api_token: bool = False
    self.has_anthropic_api_token: bool = False
    self.has_local_llm_api_token: bool = False
    self.has_runpod_api_token: bool = False
    self.has_massed_compute_api_token: bool = False
    self.has_zammad_api_token: bool = False
    self.has_openrouter_api_token: bool = False
    self.has_huggingface_api_token: bool = False
    self.has_cloudflare_api_token: bool = False

  def load_all_prompts(self) -> list[LLMPromptStore]:
    # Load default prompts
    for prompt in self.DEFAULT_PROMPTS:
      if not self.prompt_exists(prompt['name']):
        self.prompt_store.append(LLMPromptStore(self.prompt_store_directory, prompt['name'], prompt['title'], prompt['prompt'], prompt['description']))
      else:
        pass
        # TODO: log error, prompt name already exists

    # Load function calling prompt
    if not self.prompt_exists(self.FUNCTION_CALLING_PROMPT_NAME):
      self.prompt_store.append(
        LLMPromptStore(
          self.prompt_store_directory,
          self.FUNCTION_CALLING_PROMPT_NAME,
          "Function Calling Assistant",
          function_calling_prompt,
          "An assistant capable of calling functions."
        )
      )
    else:
      pass
      # TODO: log error, function calling prompt name already exists

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

  def load_from_env(self) -> None:
    """
    Load configuration settings from environment variables.
    """
    def strip_quotes(value: str) -> str:
      return value.strip("\"'") if value else value

    self.openai_api_token = strip_quotes(os.environ.get("TOKEN_OPENAI", ""))
    self.has_openai_api_token = bool(self.openai_api_token)

    self.anthropic_api_token = strip_quotes(os.environ.get("TOKEN_ANTHROPIC", ""))
    self.has_anthropic_api_token = bool(self.anthropic_api_token)

    self.local_llm_api_token = strip_quotes(os.environ.get("TOKEN_LOCAL", ""))
    self.has_local_llm_api_token = bool(self.local_llm_api_token)

    self.runpod_api_token = strip_quotes(os.environ.get("TOKEN_RUNPOD", ""))
    self.has_runpod_api_token = bool(self.runpod_api_token)

    self.local_llm_base_url = strip_quotes(os.environ.get("LOCALLLM_BASEURL", ""))

    self.massed_compute_api_token = strip_quotes(os.environ.get("TOKEN_MASSEDCOMPUTE", ""))
    self.has_massed_compute_api_token = bool(self.massed_compute_api_token)

    self.zammad_api_token = strip_quotes(os.environ.get("TOKEN_ZAMMAD", ""))
    self.has_zammad_api_token = bool(self.zammad_api_token)

    self.zammad_base_url = strip_quotes(os.environ.get("ZAMMAD_BASEURL", ""))
    self.prompt_store_directory = strip_quotes(os.environ.get("PROMPT_STORE_DIRECTORY", self.prompt_store_directory))
    self.chat_history_directory = strip_quotes(os.environ.get("CHAT_HISTORY_DIRECTORY", self.chat_history_directory))
    self.model_directory = strip_quotes(os.environ.get("MODEL_DIRECTORY", self.model_directory))
    self.active_model = strip_quotes(os.environ.get("ACTIVE_MODEL", self.active_model))
    self.active_model_source = strip_quotes(os.environ.get("ACTIVE_MODEL_SOURCE", self.active_model_source))
    self.log_level = os.environ.get("LOG_LEVEL", self.log_level).lower()

    self.openrouter_api_token = strip_quotes(os.environ.get("TOKEN_OPENROUTER", ""))
    self.has_openrouter_api_token = bool(self.openrouter_api_token)
    
    self.huggingface_api_token = strip_quotes(os.environ.get("TOKEN_HUGGINGFACE", ""))
    self.has_huggingface_api_token = bool(self.huggingface_api_token)
    
    self.cloudflare_api_token = strip_quotes(os.environ.get("TOKEN_CLOUDFLARE", ""))
    self.has_cloudflare_api_token = bool(self.cloudflare_api_token)
    
    # Load VLLM specific settings
    self.vllm_zone = strip_quotes(os.environ.get("VLLM_ZONE", ""))
    self.vllm_email = strip_quotes(os.environ.get("VLLM_EMAIL", ""))
    self.vllm_subdomain = strip_quotes(os.environ.get("VLLM_SUBDOMAIN", ""))

  def load_from_args(self, args: argparse.Namespace) -> None:
    """
    Load configuration settings from command-line arguments.

    Args:
      args (argparse.Namespace): Parsed command-line arguments.
    """
    for key, value in vars(args).items():
      if value is not None:
        setattr(self, key, value)
        if key.endswith('_api_token'):
          setattr(self, f'has_{key}', bool(value))

  def validate(self) -> bool:
    """
    Validate the configuration settings.

    Returns:
      bool: True if at least one API token is present, False otherwise.
    """
    if self.log_level not in self.LOG_LEVELS:
      print(f"Invalid log level in environment variable. Using default: {self.log_level}")
      self.log_level = "info"

    api_tokens_present = (
      self.has_openai_api_token or
      self.has_anthropic_api_token or
      self.has_local_llm_api_token or
      self.has_runpod_api_token or
      self.has_massed_compute_api_token or
      self.has_zammad_api_token or
      self.has_openrouter_api_token or
      self.has_huggingface_api_token or
      self.has_cloudflare_api_token
    )

    if not api_tokens_present:
      print("No API tokens found. At least one API token is required.")

    return api_tokens_present

class SettingsFactory:
  """
  Factory class for creating and loading Settings objects.
  """

  @staticmethod
  def create_settings() -> Settings:
    """
    Create and load a Settings object from environment variables and command-line arguments.

    Returns:
      Settings: A fully loaded Settings object.
    """
    settings = Settings()

    # Load from environment variables
    settings.load_from_env()

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="CLAI Settings")
    parser.add_argument("--openai-api-token", help="OpenAI API Token")
    parser.add_argument("--anthropic-api-token", help="Anthropic API Token")
    parser.add_argument("--local-llm-api-token", help="LocalLLM API Token")
    parser.add_argument("--runpod-api-token", help="RunPod API Token")
    parser.add_argument("--local-llm-base-url", help="LocalLLM Base URL")
    parser.add_argument("--massed-compute-api-token", help="Massed Compute API Token")
    parser.add_argument("--zammad-api-token", help="Zammad API Token")
    parser.add_argument("--zammad-base-url", help="Zammad Base URL")
    parser.add_argument("--prompt-store-directory", help="Prompt Store Directory")
    parser.add_argument("--chat-history-directory", help="Chat History Directory")
    parser.add_argument("--active-model", help="Active Model")
    parser.add_argument("--active-model-source", help="Active Model Source")
    parser.add_argument("--log-level",
                        choices=Settings.LOG_LEVELS.keys(),
                        help="Logging level (debug, info, warning, error, critical)")
    parser.add_argument("--openrouter-api-token", help="OpenRouter API Token")
    parser.add_argument("--huggingface-api-token", help="Hugging Face API Token")
    parser.add_argument("--cloudflare-api-token", help="Cloudflare API Token")
    parser.add_argument("--vllm-zone", help="VLLM Zone")
    parser.add_argument("--vllm-email", help="VLLM Email")
    parser.add_argument("--vllm-subdomain", help="VLLM Subdomain")
    args = parser.parse_args()

    # Load from command-line arguments (overrides environment variables)
    settings.load_from_args(args)

    return settings

# Usage example
if __name__ == "__main__":
  settings = SettingsFactory.create_settings()
  if settings.validate():
    print("Settings loaded successfully")
  else:
    print("Error loading settings")
