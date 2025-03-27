"""
This module contains the prompt file handling class for CLAIA.
"""

# TODO:
# - Double check the save method. If content is passed, is the metadata inconsistent?
# - Move save override stuff to post save hook


# External dependencies
import json
import re
import logging
from typing import Dict, Any, Optional, Type, TypeVar, Union, List

# Internal dependencies
from .text import TextFile
from enums.file import FileSubdirectory



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

# Type variable for class methods
T = TypeVar('T', bound='Prompt')



########################################################################
#                             PROMPT CLASS                             #
########################################################################
class Prompt(TextFile):
  """
  Class for handling prompt files with specialized functionality.
  
  Features:
  - Stores prompts in JSON format
  - Validates prompt name (lowercase with hyphens)
  - Inherits text file functionality for content operations
  - Supports placeholder replacement in prompt templates
  - Handles function definition formats for LLM function calling
  """
  
  def __init__(self, base_directory: str, **kwargs):
    """
    Initialize a prompt file.
    
    Args:
      base_directory (str): Base directory for the file
      **kwargs: Additional arguments to pass to the parent class
    """
    # Extract prompt-specific kwargs
    self.prompt_name = kwargs.pop("prompt_name", None)
    self.prompt_text = kwargs.pop("prompt_text", "")
    
    # Ensure the file has .json extension
    file_name = kwargs.get("file_name")
    if file_name and not file_name.endswith(".json"):
      kwargs["file_name"] = f"{file_name}.json"
    
    # Initialize as TextFile but ensure mime_type is application/json
    kwargs["mime_type"] = "application/json"
    super().__init__(base_directory=base_directory, **kwargs)
    
    # Update the prompt name if provided
    if self.prompt_name:
      self.prompt_name = self.validate_prompt_name(self.prompt_name)
    
    # Add prompt-specific metadata
    self.metadata.update({
      "prompt_name": self.prompt_name,
      "prompt_type": "text"  # Default type, can be extended later
    })
    
    # Store function definitions separately (not persisted)
    self.function_definitions = []
  
  def get_subdirectory(self) -> str:
    """
    Override to return the prompts subdirectory regardless of mime type.
    
    Returns:
      str: The prompts subdirectory
    """
    return FileSubdirectory.PROMPT.value
  
  @staticmethod
  def validate_prompt_name(name: str) -> str:
    """
    Validate and format a prompt name to be lowercase with hyphens.
    
    Args:
      name (str): Prompt name to validate
      
    Returns:
      str: Validated prompt name (lowercase with hyphens)
    """
    if not name:
      return ""
    
    # Convert to lowercase
    name = name.lower()
    
    # Replace spaces with hyphens
    name = re.sub(r'\s+', '-', name)
    
    # Remove any characters that aren't alphanumeric or hyphens
    name = re.sub(r'[^a-z0-9-]', '', name)
    
    # Replace multiple consecutive hyphens with a single hyphen
    name = re.sub(r'-+', '-', name)
    
    # Remove leading/trailing hyphens
    name = name.strip('-')
    
    return name
  
  def get_prompt_data(self) -> Dict[str, Any]:
    """
    Get the prompt data as a dictionary.
    
    Returns:
      Dict[str, Any]: Prompt data with name and text
    """
    # If already loaded, return the cached data
    if hasattr(self, '_prompt_data'):
      return self._prompt_data
    
    # Try to load from file if it exists
    if self.exists():
      try:
        content = self.get_content()
        data = json.loads(content)
        self.prompt_name = data.get("name", "")
        self.prompt_text = data.get("prompt", "")
        
        # Update metadata
        self.metadata.update({
          "prompt_name": self.prompt_name,
          "prompt_text_preview": self.prompt_text[:50] + "..." if len(self.prompt_text) > 50 else self.prompt_text
        })
        
        # Cache the data
        self._prompt_data = data
        return data
      except json.JSONDecodeError:
        logger.error(f"Failed to parse JSON from prompt file: {self.file_id}")
    
    # Return default data if file doesn't exist or parsing failed
    default_data = {"name": self.prompt_name or "", "prompt": self.prompt_text or ""}
    self._prompt_data = default_data
    return default_data
  
  def save(self, content: Optional[Union[str, bytes]] = None, encoding: str = "utf-8") -> Optional[str]:
    """
    Save the prompt file.
    
    This overrides the parent save method to handle saving the prompt data.
    
    Args:
      content: Optional content to write (overrides current prompt data if provided)
      encoding: Encoding to use when writing the content
      
    Returns:
      Optional[str]: The path to the saved file, or None if saving failed
    """
    # If content is provided, use that (allows saving arbitrary JSON content)
    if content is not None:
      saved_path = super().save(content=content, encoding=encoding)
      # After saving, reload the prompt data to keep it in sync
      if saved_path:
        self.get_prompt_data()  # This will refresh the cached data
      return saved_path
    
    # Otherwise, construct JSON from prompt data
    validated_name = self.validate_prompt_name(self.prompt_name) if self.prompt_name else ""
    prompt_data = {
      "name": validated_name,
      "prompt": self.prompt_text or ""
    }
    
    # Update cached data
    self._prompt_data = prompt_data
    
    # Update metadata
    self.metadata.update({
      "prompt_name": validated_name,
      "prompt_text_preview": self.prompt_text[:50] + "..." if len(self.prompt_text) > 50 else self.prompt_text
    })
    
    # Convert to JSON string
    json_content = json.dumps(prompt_data, indent=2)
    
    # Save using parent method
    return super().save(content=json_content, encoding=encoding)
  
  def load_function_definitions(self, function_definitions: List[Dict[str, Any]]) -> None:
    """
    Load function definitions into the prompt.
    This should be called before using the prompt to ensure it has the latest function definitions.

    Args:
      function_definitions: List of function definitions to load
    """
    self.function_definitions = function_definitions
    logger.debug(f"Loaded {len(function_definitions)} function definitions into prompt {self.prompt_name}")
  
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
  def create_prompt(cls: Type[T], base_directory: str, prompt_name: str, 
                   prompt_text: str, **kwargs) -> Optional[T]:
    """
    Create a new prompt file.
    
    Args:
      base_directory (str): Base directory for the file
      prompt_name (str): Name for the prompt (will be validated)
      prompt_text (str): Text content of the prompt
      **kwargs: Additional arguments to pass to the constructor
      
    Returns:
      Optional[T]: A new Prompt instance, or None if creation failed
    """
    # Validate the prompt name
    validated_name = cls.validate_prompt_name(prompt_name)
    
    # Use validated name as file name if none provided
    if "file_name" not in kwargs:
      kwargs["file_name"] = f"{validated_name}.json"
    
    # Create the prompt instance
    prompt = cls(
      base_directory=base_directory,
      prompt_name=validated_name,
      prompt_text=prompt_text,
      **kwargs
    )
    
    # Save the prompt to disk
    if prompt.save() is None:
      logger.error(f"Failed to save prompt: {validated_name}")
      return None
    
    return prompt
  
  @classmethod
  def load_prompt(cls: Type[T], prompt_name: str, base_directory: str) -> Optional[T]:
    """
    Load a prompt by name.
    
    Args:
      prompt_name (str): Name of the prompt to load
      base_directory (str): Base directory for file operations
      
    Returns:
      Optional[T]: The loaded prompt, or None if loading failed
    """
    # Validate the prompt name
    validated_name = cls.validate_prompt_name(prompt_name)
    file_name = f"{validated_name}.json"
    
    # Use the BaseFile.find_files_by_criteria method to find prompts matching the name
    # First try to find by file name
    matching_files = cls.find_files_by_criteria(
      base_directory=base_directory, 
      subdirectory=FileSubdirectory.PROMPT.value,
      metadata_filters={"file_name": file_name}
    )
    
    # If no match by file name, try by prompt_name in metadata
    if not matching_files:
      matching_files = cls.find_files_by_criteria(
        base_directory=base_directory,
        subdirectory=FileSubdirectory.PROMPT.value,
        metadata_filters={"metadata.prompt_name": validated_name}
      )
    
    # Load the first matching file
    for file_id in matching_files:
      prompt = cls.load(file_id, base_directory)
      if prompt:
        # Load prompt data explicitly
        prompt.get_prompt_data()
        return prompt
    
    logger.error(f"Prompt not found: {prompt_name}")
    return None

  def _post_save_hook(self):
    """
    Update prompt statistics and data after saving.
    
    This is called automatically after save() completes.
    """
    # Call parent's post save hook for text stats
    super()._post_save_hook()
    
    # Only update prompt data if the file exists
    if self.exists():
      # Clear cached data to force refresh
      if hasattr(self, '_prompt_data'):
        delattr(self, '_prompt_data')
      
      # Reload prompt data to ensure everything is in sync
      self.get_prompt_data() 