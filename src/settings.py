"""
This module manages the configuration settings for the CLAI application.

It provides a Settings class to store settings and a SettingsFactory to create
and load settings from various sources (environment variables and command-line arguments).
"""

import os
from typing import Dict, Optional
import argparse
from file import LLMPromptStore, ChatHistory

class Settings:
  """
  Stores and manages configuration settings for the CLAI application.

  Attributes:
    openai_api_token (str): API token for OpenAI.
    anthropic_api_token (str): API token for Anthropic.
    local_llm_api_token (str): API token for local LLM.
    local_llm_base_url (str): Base URL for local LLM.
    massed_compute_api_token (str): API token for Massed Compute.
    selected_llm (str): Currently selected LLM.
    prompt_store_directory (str): Directory to store LLM prompt stores.
    chat_history_directory (str): Directory to store chat histories.
    active_prompt (Optional[LLMPromptStore]): Currently active system prompt.
    active_chat (Optional[ChatHistory]): Currently active chat history.
  """

  def __init__(self):
    print("Initializing Settings")
    self.openai_api_token: str = ""
    self.anthropic_api_token: str = ""
    self.local_llm_api_token: str = ""
    self.local_llm_base_url: str = ""
    self.massed_compute_api_token: str = ""
    self.selected_llm: str = "0"
    self.prompt_store_directory: str = "prompts"
    self.chat_history_directory: str = "history"
    self.active_prompt: LLMPromptStore = LLMPromptStore.load_default_or_first(self.prompt_store_directory)
    self.active_chat: ChatHistory = ChatHistory(self.chat_history_directory, "New Conversation", [])

  def load_from_env(self) -> None:
    """
    Load configuration settings from environment variables.
    """
    def strip_quotes(value: str) -> str:
      return value.strip("\"'") if value else value

    self.openai_api_token = strip_quotes(os.environ.get("TOKEN_OPENAI", self.openai_api_token))
    self.anthropic_api_token = strip_quotes(os.environ.get("TOKEN_ANTHROPIC", self.anthropic_api_token))
    self.local_llm_api_token = strip_quotes(os.environ.get("TOKEN_LOCAL", self.local_llm_api_token))
    self.local_llm_base_url = strip_quotes(os.environ.get("LOCALLLM_BASEURL", self.local_llm_base_url))
    self.massed_compute_api_token = strip_quotes(os.environ.get("TOKEN_MASSEDCOMPUTE", self.massed_compute_api_token))
    self.prompt_store_directory = strip_quotes(os.environ.get("PROMPT_STORE_DIRECTORY", self.prompt_store_directory))
    self.chat_history_directory = strip_quotes(os.environ.get("CHAT_HISTORY_DIRECTORY", self.chat_history_directory))

  def load_from_args(self, args: argparse.Namespace) -> None:
    """
    Load configuration settings from command-line arguments.

    Args:
      args (argparse.Namespace): Parsed command-line arguments.
    """
    for key, value in vars(args).items():
      if value is not None:
        setattr(self, key, value)

  def validate(self) -> bool:
    """
    Validate the configuration settings.

    Returns:
      bool: True if all required settings are present, False otherwise.
    """
    required_tokens = [
      ("OpenAI API Token", self.openai_api_token),
      ("Anthropic API Token", self.anthropic_api_token),
      ("LocalLLM API Token", self.local_llm_api_token),
      ("LocalLLM Base URL", self.local_llm_base_url),
      ("Massed Compute API Token", self.massed_compute_api_token),
    ]

    is_valid = True
    for name, token in required_tokens:
      if not token:
        print(f"No {name} found")
        is_valid = False

    return is_valid

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
    parser.add_argument("--local-llm-base-url", help="LocalLLM Base URL")
    parser.add_argument("--massed-compute-api-token", help="Massed Compute API Token")
    parser.add_argument("--selected-llm", help="Selected LLM")
    parser.add_argument("--prompt-store-directory", help="Prompt Store Directory")
    parser.add_argument("--chat-history-directory", help="Chat History Directory")
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

