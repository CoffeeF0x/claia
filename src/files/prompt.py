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
    
    # Set the subdirectory override before calling the parent constructor
    self._override_subdirectory = FileSubdirectory.PROMPT.value
    
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
  
  def _get_default_content(self) -> Optional[str]:
    """
    Provide default content when saving without content.
    
    Returns:
      str: JSON representation of the prompt
    """
    # Construct prompt data
    prompt_data = {
      "name": self.prompt_name,
      "prompt": self.prompt_text or ""
    }

    return json.dumps(prompt_data, indent=2)

  def _post_save_hook(self):
    """
    Update prompt metadata after saving.
    
    This is called automatically after save() completes.
    """
    # Call parent's post save hook for text stats
    super()._post_save_hook()

    # Update metadata
    self.metadata.update({
      "prompt_name": self.prompt_name,
      "prompt_text_preview": self.prompt_text[:50] + "..." if len(self.prompt_text) > 50 else self.prompt_text
    })
    
    # Save metadata to ensure it's up to date in the manifest
    self.save_metadata()
  
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
      result = cls.load(file_id, base_directory, load_content=True)
      if result and "content" in result:
        try:
          # Parse the JSON content
          data = json.loads(result["content"])
          
          # Extract valid constructor parameters from metadata
          metadata = result["metadata"].get("metadata", {})
          
          # Create a new Prompt instance with the loaded data
          prompt = cls(
            base_directory=base_directory,
            file_id=result["metadata"].get("file_id"),
            file_name=result["metadata"].get("file_name"),
            mime_type=result["metadata"].get("mime_type"),
            timestamp=result["metadata"].get("timestamp"),
            prompt_name=data.get("name", ""),
            prompt_text=data.get("prompt", ""),
            metadata=metadata
          )
          return prompt
        except json.JSONDecodeError:
          logger.error(f"Failed to parse JSON from prompt file: {file_id}")
          continue
    
    logger.error(f"Prompt not found: {prompt_name}")
    return None