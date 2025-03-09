"""
This module contains the base file handling functionality for CLAIA.
It defines the base class for file operations used throughout the application.
"""

# External dependencies
import json
import os
import uuid
import logging
from typing import Dict, List, Any, Optional, Type, TypeVar, Generic



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)

# Type variable for class methods that return the class instance
T = TypeVar('T', bound='BaseFile')



########################################################################
#                              BASE CLASS                              #
########################################################################
class BaseFile:
  """
  Base class for all file-related operations in CLAIA.

  This class provides common functionality for file operations such as:
  - Directory creation and validation
  - File saving and loading
  - File listing and existence checking

  All classes that deal with file operations should inherit from this class.
  """

  def __init__(self, base_directory: str):
    """
    Initialize a BaseFile object.

    Args:
        base_directory: The base directory for file operations
    """
    self.base_directory = base_directory
    self.unique_id = str(uuid.uuid4())

  def ensure_directory_exists(self) -> bool:
    """
    Ensure that the base directory exists.

    Returns:
        bool: True if the directory exists or was created, False otherwise
    """
    try:
      os.makedirs(self.base_directory, exist_ok=True)
      return True
    except Exception as e:
      logger.error(f"Failed to create directory {self.base_directory}: {e}")
      return False

  def get_full_path(self, filename: str) -> str:
    """
    Get the full path for a file.

    Args:
        filename: The name of the file

    Returns:
        str: The full path to the file
    """
    return os.path.join(self.base_directory, filename)

  def file_exists(self, filename: str) -> bool:
    """
    Check if a file exists.

    Args:
        filename: The name of the file

    Returns:
        bool: True if the file exists, False otherwise
    """
    return os.path.exists(self.get_full_path(filename))

  def save(self, filename: str) -> Optional[str]:
    """
    Save the object to a file.

    Args:
        filename: The name of the file

    Returns:
        Optional[str]: The full path to the saved file, or None if saving failed
    """
    try:
      full_path = self.get_full_path(filename)
      self.ensure_directory_exists()

      with open(full_path, 'w') as file:
        json.dump(self.to_dict(), file, indent=2)

      return full_path
    except Exception as e:
      logger.error(f"Failed to save file {filename}: {e}")
      return None

  @classmethod
  def load(cls: Type[T], filename: str, base_directory: str) -> Optional[T]:
    """
    Load an object from a file.

    Args:
        filename: The name of the file
        base_directory: The base directory for file operations

    Returns:
        Optional[T]: The loaded object, or None if loading failed
    """
    try:
      full_path = os.path.join(base_directory, filename)

      if not os.path.exists(full_path):
        logger.error(f"File {full_path} does not exist")
        return None

      with open(full_path, 'r') as file:
        data = json.load(file)

      return cls.from_dict(data, base_directory)
    except Exception as e:
      logger.error(f"Failed to load file {filename}: {e}")
      return None

  def to_dict(self) -> Dict[str, Any]:
    """
    Convert the object to a dictionary.

    Returns:
        Dict[str, Any]: The object as a dictionary
    """
    raise NotImplementedError("Subclasses must implement to_dict method")

  @classmethod
  def from_dict(cls: Type[T], data: Dict[str, Any], base_directory: str) -> T:
    """
    Create an object from a dictionary.

    Args:
        data: The dictionary containing the object data
        base_directory: The base directory for file operations

    Returns:
        T: The created object
    """
    raise NotImplementedError("Subclasses must implement from_dict method")

  @staticmethod
  def list_files(directory: str, extension: str = '.json') -> List[str]:
    """
    List all files in a directory with a specific extension.

    Args:
        directory: The directory to list files from
        extension: The file extension to filter by

    Returns:
        List[str]: A list of filenames
    """
    try:
      if not os.path.exists(directory):
        logger.warning(f"Directory {directory} does not exist")
        return []

      return [f for f in os.listdir(directory) if f.endswith(extension)]
    except Exception as e:
      logger.error(f"Failed to list files in {directory}: {e}")
      return []

  @staticmethod
  def ensure_directory(directory: str) -> bool:
    """
    Static method to ensure a directory exists.

    Args:
        directory: The directory to ensure exists

    Returns:
        bool: True if the directory exists or was created, False otherwise
    """
    try:
      os.makedirs(directory, exist_ok=True)
      return True
    except Exception as e:
      logger.error(f"Failed to create directory {directory}: {e}")
      return False

  @staticmethod
  def safe_delete_file(filepath: str) -> bool:
    """
    Safely delete a file if it exists.

    Args:
        filepath: The path to the file to delete

    Returns:
        bool: True if the file was deleted or didn't exist, False if deletion failed
    """
    try:
      if os.path.exists(filepath):
        os.remove(filepath)
      return True
    except Exception as e:
      logger.error(f"Failed to delete file {filepath}: {e}")
      return False