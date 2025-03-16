"""
This module contains the prompt store functionality for CLAIA.
It defines classes for managing and storing LLM prompts.
"""

# External dependencies
import os
import json
import uuid
import logging
from typing import Dict, Optional, List, Any, Type, TypeVar

# Internal dependencies
from conversations.config import Config



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)

# Type variable for class methods that return the class instance
T = TypeVar('T', bound='Prompt')



########################################################################
#                              CONSTANTS                               #
########################################################################
# Default function format placeholder
DEFAULT_FUNCTION_FORMAT = """
[FUNCTION_CALL]{
"name": "function_name",
"parameters": {
  "param1": "value1",
  "param2": "value2"
}
}[/FUNCTION_CALL]
"""



########################################################################
#                             PROMPT CLASS                             #
########################################################################
class Prompt(Config):
  """
  Represents a reusable prompt template that can be used in conversations.
  """

  def __init__(self,
               base_directory: str,
               name: str,
               title: str,
               prompt: str,
               description: Optional[str] = None,
               prompt_id: Optional[str] = None,
               tags: Optional[List[str]] = None,
               created_at: Optional[float] = None,
               updated_at: Optional[float] = None):
    """
    Initialize a Prompt object.

    Args:
        base_directory: Base directory for storing prompts
        name: Unique name for the prompt (used as identifier)
        title: Display title for the prompt
        prompt: The prompt template text
        description: Optional description of the prompt
        prompt_id: Optional unique ID (generated if not provided)
        tags: Optional list of tags for categorization
        created_at: Optional timestamp for creation time
        updated_at: Optional timestamp for last update time
    """
    # Format the name to be used as an identifier
    formatted_name = self.validate_and_format_name(name)

    # Initialize the config with prompt-specific properties
    super().__init__(
      base_directory=base_directory,
      name=prompt_id or formatted_name,
      title=title,
      prompt=prompt,
      description=description or "",
      tags=tags or [],
      created_at=created_at,
      updated_at=updated_at
    )

    # Store function definitions separately (not persisted)
    self.function_definitions = []

  @staticmethod
  def validate_and_format_name(name: str) -> str:
    """
    Validate and format a prompt name to be used as an identifier.

    Args:
        name: The prompt name to validate and format

    Returns:
        str: The validated and formatted name
    """
    return name.lower().replace(' ', '-')

  def get_name(self) -> str:
    """Get the prompt name."""
    return self.get("name")

  @property
  def title(self) -> str:
    """Get the prompt title."""
    return self.get("title")

  @property
  def prompt_text(self) -> str:
    """Get the prompt template text."""
    return self.get("prompt")

  @property
  def description(self) -> str:
    """Get the prompt description."""
    return self.get("description", "")

  @property
  def tags(self) -> List[str]:
    """Get the prompt tags."""
    return self.get("tags", [])

  def load_function_definitions(self, function_definitions: List[Dict[str, Any]]) -> None:
    """
    Load function definitions into the prompt.
    This should be called before using the prompt to ensure it has the latest function definitions.

    Args:
        function_definitions: List of function definitions to load
    """
    self.function_definitions = function_definitions
    logger.debug(f"Loaded {len(function_definitions)} function definitions into prompt {self.get_name()}")

  def format(self, **kwargs) -> str:
    """
    Format the prompt with the given replacements if the matching placeholders are found.
    Currently supports 'function_definitions' and 'function_format' placeholders.

    Args:
        **kwargs: Keyword arguments for string formatting

    Returns:
        str: The formatted prompt
    """
    formatted_prompt = self.prompt_text

    # Check if the prompt contains function_definitions placeholder
    if "{function_definitions}" in formatted_prompt and "function_definitions" not in kwargs:
      # Use the stored function definitions if available, otherwise use empty list
      function_definitions_json = json.dumps(self.function_definitions, indent=2)
      kwargs["function_definitions"] = function_definitions_json

    # Check if the prompt contains function_format placeholder
    if "{function_format}" in formatted_prompt and "function_format" not in kwargs:
      kwargs["function_format"] = DEFAULT_FUNCTION_FORMAT

    # Only attempt formatting if there are placeholders to replace
    if kwargs and any(f"{{{key}}}" in formatted_prompt for key in kwargs):
      try:
        formatted_prompt = formatted_prompt.format(**kwargs)
      except KeyError as e:
        logger.warning(f"Missing key in prompt formatting: {e}")
      except Exception as e:
        logger.error(f"Error formatting prompt: {e}")

    return formatted_prompt

  def get_formatted_prompt(self, **kwargs) -> str:
    """
    Get the formatted prompt.

    Args:
        **kwargs: Additional keyword arguments for formatting

    Returns:
        str: The formatted prompt
    """
    return self.format(**kwargs)

  @classmethod
  def load(cls: Type[T], name: str, base_directory: str) -> Optional[T]:
    """
    Load a prompt by name.

    Args:
        name: The name of the prompt to load
        base_directory: The base directory for prompt storage

    Returns:
        Optional[T]: The loaded prompt, or None if loading failed
    """
    # Format the name to match how it would be stored
    formatted_name = cls.validate_and_format_name(name)
    return super().load(formatted_name, base_directory)

  @classmethod
  def list_prompts(cls, base_directory: str) -> List[Dict[str, Any]]:
    """
    List all prompts in the directory.

    Args:
        base_directory: The base directory for prompt storage

    Returns:
        List[Dict[str, Any]]: A list of prompt metadata
    """
    return cls.list_configs(base_directory)

  @classmethod
  def get_prompt_names(cls, base_directory: str) -> List[str]:
    """
    Get a list of all prompt names from the prompt files in the directory.

    Args:
        base_directory: The base directory for prompt storage

    Returns:
        List[str]: A list of prompt names
    """
    prompts = cls.list_prompts(base_directory)
    return [prompt.get("name", "") for prompt in prompts if prompt.get("name")]