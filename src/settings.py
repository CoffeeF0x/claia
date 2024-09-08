"""
This module manages the configuration settings for the CLAI application.

It provides a Settings class to store settings and a SettingsFactory to create
and load settings from various sources (environment variables and command-line arguments).
"""

import os
import uuid
from typing import Dict, Any
import argparse

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
    selected_conversation (str): Currently selected conversation.
    selected_character (str): Currently selected character.
    conversation_directory (str): Directory to store conversations.
    conversation (list): List to store conversation history.
    characters (Dict[str, Dict[str, str]]): Dictionary of available characters.
  """

  def __init__(self):
    self.openai_api_token: str = ""
    self.anthropic_api_token: str = ""
    self.local_llm_api_token: str = ""
    self.local_llm_base_url: str = ""
    self.massed_compute_api_token: str = ""
    self.selected_llm: str = "0"
    self.selected_conversation: str = f"{str(uuid.uuid4())}.json"
    self.selected_character: str = "writer"
    self.conversation_directory: str = "history"
    self.conversation: list[str] = []
    self.characters: Dict[str, Dict[str, str]] = {
      "default": {
        "role": "system",
        "content": "You are a poetic assistant, skilled in explaining complex programming concepts with creative flair."
      },
      "writer": {
        "role": "system",
        "content": "You are a brilliant writer, always adding events and details that give life to the story, making sure to show and not tell about environments, characters, and actions."
      }
    }

  def load_from_env(self) -> None:
    """
    Load configuration settings from environment variables.
    """
    self.openai_api_token = os.environ.get("TOKEN_OPENAI", self.openai_api_token)
    self.anthropic_api_token = os.environ.get("TOKEN_ANTHROPIC", self.anthropic_api_token)
    self.local_llm_api_token = os.environ.get("TOKEN_LOCAL", self.local_llm_api_token)
    self.local_llm_base_url = os.environ.get("LOCALLLM_BASEURL", self.local_llm_base_url)
    self.massed_compute_api_token = os.environ.get("TOKEN_MASSEDCOMPUTE", self.massed_compute_api_token)
    self.selected_character = os.environ.get("SELECTED_CHARACTER", self.selected_character)
    self.conversation_directory = os.environ.get("CONVERSATION_DIRECTORY", self.conversation_directory)
    self.selected_conversation = os.environ.get("SELECTED_CONVERSATION", self.selected_conversation)

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
    parser.add_argument("--selected-character", help="Selected Character")
    parser.add_argument("--conversation-directory", help="Conversation Directory")
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
