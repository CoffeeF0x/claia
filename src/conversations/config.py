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
from conversations.base import BaseFile



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
               config_id: str,
               base_directory: str,
               config_type: str = "config",
               **kwargs):
    """
    Initialize a Config object.

    Args:
        config_id: Unique identifier for this configuration
        base_directory: Base directory for storing configurations
        config_type: Type of configuration (used for subdirectory)
        **kwargs: Additional configuration properties
    """
    # Initialize with a path in the appropriate config subdirectory
    file_path = os.path.join(base_directory, config_type, f"{config_id}.json")
    super().__init__(file_path=file_path, base_directory=base_directory)

    self.config_id = config_id
    self.config_type = config_type
    self.created_at = kwargs.pop('created_at', time.time())
    self.updated_at = kwargs.pop('updated_at', self.created_at)

    # Store all remaining kwargs as configuration properties
    self.properties = kwargs

  def get_subdirectory(self) -> str:
    """
    Override the get_subdirectory method to use config_type.

    Returns:
        str: The subdirectory for this config type
    """
    return self.config_type

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
      "config_id": self.config_id,
      "config_type": self.config_type,
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
    config_id = data.pop("config_id")
    config_type = data.pop("config_type", "config")
    created_at = data.pop("created_at", time.time())
    updated_at = data.pop("updated_at", created_at)

    # Create the instance with remaining properties
    return cls(
      config_id=config_id,
      base_directory=base_directory,
      config_type=config_type,
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
      config_dir = os.path.join(self.base_directory, self.config_type)
      os.makedirs(config_dir, exist_ok=True)

      # Save to JSON file
      file_path = os.path.join(config_dir, f"{self.config_id}.json")
      with open(file_path, 'w') as f:
        json.dump(self.to_dict(), f, indent=2)

      return file_path
    except Exception as e:
      logger.error(f"Failed to save configuration {self.config_id}: {e}")
      return None

  @classmethod
  def load(cls: Type[T], config_id: str, base_directory: str, config_type: str = "config") -> Optional[T]:
    """
    Load a configuration from a file.

    Args:
        config_id: ID of the configuration to load
        base_directory: Base directory for configurations
        config_type: Type of configuration (subdirectory)

    Returns:
        Optional[T]: The loaded configuration, or None if loading failed
    """
    try:
      file_path = os.path.join(base_directory, config_type, f"{config_id}.json")

      if not os.path.exists(file_path):
        logger.error(f"Configuration file {file_path} does not exist")
        return None

      with open(file_path, 'r') as f:
        data = json.load(f)

      return cls.from_dict(data, base_directory)
    except Exception as e:
      logger.error(f"Failed to load configuration {config_id}: {e}")
      return None

  @classmethod
  def list_configs(cls, base_directory: str, config_type: str = "config") -> List[Dict[str, Any]]:
    """
    List all configurations of a specific type.

    Args:
        base_directory: Base directory for configurations
        config_type: Type of configuration to list

    Returns:
        List[Dict[str, Any]]: List of configuration metadata
    """
    try:
      config_dir = os.path.join(base_directory, config_type)

      if not os.path.exists(config_dir):
        logger.warning(f"Configuration directory {config_dir} does not exist")
        return []

      config_files = [f for f in os.listdir(config_dir) if f.endswith('.json')]
      configs = []

      for file_name in config_files:
        try:
          file_path = os.path.join(config_dir, file_name)
          with open(file_path, 'r') as f:
            data = json.load(f)

          # Extract basic metadata
          configs.append({
            "config_id": data.get("config_id"),
            "config_type": data.get("config_type", config_type),
            "updated_at": data.get("updated_at", 0)
          })
        except Exception as e:
          logger.error(f"Failed to read configuration file {file_name}: {e}")

      # Sort by updated_at, newest first
      configs.sort(key=lambda x: x.get("updated_at", 0), reverse=True)

      return configs
    except Exception as e:
      logger.error(f"Failed to list configurations: {e}")
      return []