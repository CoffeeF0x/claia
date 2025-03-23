"""
This module contains configuration management functionality for CLAIA.
It defines classes for managing JSON-based configurations.
"""

# External dependencies
import os
import json
import logging
import time
from typing import Dict, Any, Optional, List, Type, TypeVar, Generic

# Internal dependencies
from .base import BaseFile



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)

# Type variable for class methods that return the class instance
T = TypeVar('T', bound='Config')



########################################################################
#                             CONFIG CLASS                             #
########################################################################
class Config(BaseFile):
  """
  Base class for configuration management.

  This class provides functionality for loading, saving, and managing
  configuration data stored in JSON format.
  """

  def __init__(self,
               name: str,
               base_directory: str,
               **kwargs):
    """
    Initialize a Config object.

    Args:
        name: Name for this configuration (used as identifier)
        base_directory: Base directory for storing configurations
        **kwargs: Additional configuration properties
    """
    # Initialize with a path in the config directory
    file_path = os.path.join(base_directory, f"{name}.json")
    super().__init__(file_path=file_path, base_directory=base_directory)

    self.name = name
    self.created_at = kwargs.pop('created_at', time.time())
    self.updated_at = kwargs.pop('updated_at', self.created_at)

    # Store all remaining kwargs as configuration properties
    self.properties = kwargs

  def get_subdirectory(self) -> str:
    """
    Override the get_subdirectory method to use the default.

    Returns:
        str: The subdirectory for configs
    """
    return ""

  def get(self, key: str, default: Any = None) -> Any:
    """
    Get a configuration property.

    Args:
        key: The property key to retrieve
        default: Default value if key doesn't exist

    Returns:
        Any: The property value or default
    """
    return self.properties.get(key, default)

  def set(self, key: str, value: Any) -> None:
    """
    Set a configuration property.

    Args:
        key: The property key to set
        value: The value to set
    """
    self.properties[key] = value
    self.updated_at = time.time()

  def update(self, properties: Dict[str, Any]) -> None:
    """
    Update multiple configuration properties.

    Args:
        properties: Dictionary of properties to update
    """
    self.properties.update(properties)
    self.updated_at = time.time()

  def to_dict(self) -> Dict[str, Any]:
    """
    Convert the configuration to a dictionary.

    Returns:
        Dict[str, Any]: The configuration as a dictionary
    """
    return {
      "name": self.name,
      "created_at": self.created_at,
      "updated_at": self.updated_at,
      **self.properties
    }

  @classmethod
  def from_dict(cls: Type[T], data: Dict[str, Any], base_directory: str) -> T:
    """
    Create a configuration from a dictionary.

    Args:
        data: Dictionary containing configuration data
        base_directory: Base directory for storing configurations

    Returns:
        T: The created configuration object
    """
    # Extract the core properties
    name = data.pop("name")
    created_at = data.pop("created_at", time.time())
    updated_at = data.pop("updated_at", created_at)

    # Create the instance with remaining properties
    return cls(
      name=name,
      base_directory=base_directory,
      created_at=created_at,
      updated_at=updated_at,
      **data
    )

  def save(self) -> Optional[str]:
    """
    Save the configuration to a file.

    Returns:
        Optional[str]: Path to the saved file, or None if saving failed
    """
    try:
      # Ensure the config directory exists
      os.makedirs(self.base_directory, exist_ok=True)

      # Save to JSON file
      file_path = os.path.join(self.base_directory, f"{self.name}.json")
      with open(file_path, 'w') as f:
        json.dump(self.to_dict(), f, indent=2)

      return file_path
    except Exception as e:
      logger.error(f"Failed to save configuration {self.name}: {e}")
      return None

  @classmethod
  def load(cls: Type[T], name: str, base_directory: str) -> Optional[T]:
    """
    Load a configuration from a file.

    Args:
        name: Name of the configuration to load
        base_directory: Base directory for configurations

    Returns:
        Optional[T]: The loaded configuration, or None if loading failed
    """
    try:
      file_path = os.path.join(base_directory, f"{name}.json")

      if not os.path.exists(file_path):
        logger.error(f"Configuration file {file_path} does not exist")
        return None

      with open(file_path, 'r') as f:
        data = json.load(f)

      return cls.from_dict(data, base_directory)
    except Exception as e:
      logger.error(f"Failed to load configuration {name}: {e}")
      return None

  @classmethod
  def list_configs(cls, base_directory: str) -> List[Dict[str, Any]]:
    """
    List all configurations.

    Args:
        base_directory: Base directory for configurations

    Returns:
        List[Dict[str, Any]]: List of configuration metadata
    """
    try:
      if not os.path.exists(base_directory):
        logger.warning(f"Configuration directory {base_directory} does not exist")
        return []

      # Get all JSON files
      config_files = [f for f in os.listdir(base_directory) if f.endswith('.json')]
      configs = []

      for file_name in config_files:
        try:
          file_path = os.path.join(base_directory, file_name)
          with open(file_path, 'r') as f:
            data = json.load(f)

          # Extract basic metadata
          configs.append({
            "name": data.get("name"),
            "updated_at": data.get("updated_at", 0)
          })
        except Exception as e:
          logger.error(f"Failed to read configuration file {file_name}: {e}")

      # Sort by updated_at, newest first
      # Use 0 as a fallback value for None to avoid comparison errors
      # TODO: Check what was causing the nonetype error
      configs.sort(key=lambda x: x.get("updated_at", 0) or 0, reverse=True)

      return configs
    except Exception as e:
      logger.error(f"Failed to list configurations: {e}")
      return []

  @classmethod
  def delete(cls, name: str, base_directory: str) -> bool:
    """
    Delete a configuration.

    Args:
        name: The name of the configuration to delete
        base_directory: The base directory for configurations

    Returns:
        bool: True if deletion succeeded, False otherwise
    """
    try:
      # Get the file path
      file_path = os.path.join(base_directory, f"{name}.json")

      # Delete the file if it exists
      if os.path.exists(file_path):
        os.remove(file_path)
        return True
      else:
        logger.warning(f"Configuration file {file_path} does not exist")
        return False
    except Exception as e:
      logger.error(f"Failed to delete configuration {name}: {e}")
      return False