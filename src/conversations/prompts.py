"""
This module contains the prompt store functionality for CLAIA.
It defines classes for managing and storing LLM prompts.
"""

# External dependencies
import os
import json
import uuid
import logging
from typing import Dict, Optional, List, Any

# Internal dependencies
from conversations.base import BaseFile



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
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                             PROMPT STORE                             #
########################################################################
class Prompt(BaseFile):
  """
  Represents a reusable prompt template that can be used in conversations.
  """

  def __init__(self,
               base_directory: str,
               name: str,
               title: str,
               prompt: str,
               description: Optional[str] = None,
               prompt_id: Optional[str] = None):
    super().__init__(base_directory)
    self.prompt_id = prompt_id or str(uuid.uuid4())
    self.name = self.validate_and_format_name(name)
    self.title = title
    self.prompt = prompt
    self.description = description
    self.created_at = __import__('time').time()
    self.updated_at = self.created_at
    self.tags = []
    self.function_definitions = []

  @staticmethod
  def validate_and_format_name(name: str) -> str:
    """
    Validate and format a prompt name.

    Args:
        name: The prompt name to validate and format

    Returns:
        str: The validated and formatted name
    """
    return name.lower().replace(' ', '-')

  def to_dict(self) -> Dict[str, Any]:
    """
    Convert the prompt to a dictionary.

    Returns:
        Dict[str, Any]: The prompt as a dictionary
    """
    return {
      "prompt_id": self.prompt_id,
      "name": self.name,
      "title": self.title,
      "prompt": self.prompt,
      "description": self.description,
      "created_at": self.created_at,
      "updated_at": self.updated_at,
      "tags": self.tags
    }

  @classmethod
  def from_dict(cls, data: Dict[str, Any], base_directory: str) -> 'Prompt':
    """
    Create a prompt from a dictionary.

    Args:
        data: The dictionary containing the prompt data
        base_directory: The base directory for file operations

    Returns:
        Prompt: The created prompt
    """
    instance = cls(
      base_directory=base_directory,
      name=data["name"],
      title=data["title"],
      prompt=data["prompt"],
      description=data.get("description"),
      prompt_id=data["prompt_id"]
    )
    instance.created_at = data.get("created_at", instance.created_at)
    instance.updated_at = data.get("updated_at", instance.updated_at)
    instance.tags = data.get("tags", [])
    return instance

  def load_function_definitions(self, function_definitions: List[Dict[str, Any]]) -> None:
    """
    Load function definitions into the prompt.
    This should be called before using the prompt to ensure it has the latest function definitions.

    Args:
        function_definitions: List of function definitions to load
    """
    self.function_definitions = function_definitions
    logger.debug(f"Loaded {len(function_definitions)} function definitions into prompt {self.name}")

  def format(self, **kwargs) -> str:
    """
    Format the prompt with the given replacements if the matching placeholders are found.
    Currently supports 'function_definitions' and 'function_format' placeholders.

    Args:
        **kwargs: Keyword arguments for string formatting

    Returns:
        str: The formatted prompt
    """
    formatted_prompt = self.prompt

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

  def save(self) -> Optional[str]:
    """
    Save the prompt to a file.

    Returns:
        Optional[str]: The path to the saved file, or None if saving failed
    """
    filename = f"{self.name}.json"
    return super().save(filename)

  @classmethod
  def load(cls, name: str, base_directory: str) -> Optional['Prompt']:
    """
    Load a prompt by name.

    Args:
        name: The name of the prompt to load
        base_directory: The base directory for file operations

    Returns:
        Optional[Prompt]: The loaded prompt, or None if loading failed
    """
    filename = f"{name}.json"
    return super().load(filename, base_directory)

  # @classmethod
  # def list_prompts(cls, base_directory: str) -> List[Dict[str, Any]]:
  #   """
  #   List all prompts in the directory.

  #   Args:
  #       base_directory: The base directory for file operations

  #   Returns:
  #       List[Dict[str, Any]]: A list of prompt metadata
  #   """
  #   prompts = []

  #   if not os.path.exists(base_directory):
  #     logger.warning(f"Prompt directory {base_directory} does not exist")
  #     return prompts

  #   # List all JSON files in the directory
  #   for filename in cls.list_files(base_directory):
  #     filepath = os.path.join(base_directory, filename)
  #     try:
  #       with open(filepath, 'r') as f:
  #         data = json.load(f)
  #         prompts.append({
  #           "prompt_id": data.get("prompt_id"),
  #           "name": data.get("name"),
  #           "title": data.get("title"),
  #           "description": data.get("description"),
  #           "tags": data.get("tags", []),
  #           "updated_at": data.get("updated_at")
  #         })
  #     except Exception as e:
  #       logger.error(f"Error loading prompt {filename}: {e}")

  #   # Sort by updated_at (newest first)
  #   prompts.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
  #   return prompts

  @classmethod
  def get_prompt_names(cls, base_directory: str) -> List[str]:
    """
    Get a list of all prompt names from the prompt files in the directory.

    Args:
        base_directory: The base directory for the prompt store

    Returns:
        List[str]: A list of prompt names
    """
    # Ensure the directory exists
    cls.ensure_directory(base_directory)

    prompt_names = []

    # List all JSON files in the directory
    for filename in cls.list_files(base_directory):
      filepath = os.path.join(base_directory, filename)
      try:
        with open(filepath, 'r') as f:
          data = json.load(f)
          if "name" in data:
            prompt_names.append(data["name"])
      except Exception as e:
        logger.error(f"Error reading prompt name from {filename}: {e}")

    return prompt_names

  @classmethod
  def load_prompts_from_directory(cls, base_directory: str) -> List['Prompt']:
    """
    Load all prompts from the prompt store directory.

    Args:
        base_directory: The base directory for the prompt store

    Returns:
        List[Prompt]: A list of all loaded prompts from the directory
    """
    # Ensure the prompt store directory exists
    cls.ensure_directory(base_directory)

    prompt_store = []

    # Load prompts from the directory
    files = cls.list_files(base_directory)
    for filename in files:
      try:
        full_path = os.path.join(base_directory, filename)
        with open(full_path, 'r') as file:
          data = json.load(file)
          prompt_store.append(cls.from_dict(data, base_directory))
      except Exception as e:
        logger.error(f"Failed to load prompt {filename}: {e}")

    return prompt_store