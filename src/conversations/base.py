"""
This module contains the base file handling functionality for CLAIA.
It defines the base class for file operations used throughout the application.
"""

# External dependencies
import json
import os
import uuid
import time
import mimetypes
import logging
from typing import Dict, List, Any, Optional, Type, TypeVar, Generic, Union
from enum import Enum



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)

# Type variable for class methods that return the class instance
T = TypeVar('T', bound='BaseFile')



########################################################################
#                              CONSTANTS                               #
########################################################################
FILE_TYPES = {
  "TEXT": ["text/plain", "text/html", "text/css", "text/javascript", "application/json", "application/xml"],
  "IMAGE": ["image/jpeg", "image/png", "image/gif", "image/svg+xml", "image/webp"],
  "AUDIO": ["audio/mpeg", "audio/wav", "audio/ogg", "audio/webm"],
  "VIDEO": ["video/mp4", "video/webm", "video/ogg"],
  "DOCUMENT": ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
  "SPREADSHEET": ["application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
  "PRESENTATION": ["application/vnd.ms-powerpoint", "application/vnd.openxmlformats-officedocument.presentationml.presentation"],
  "ARCHIVE": ["application/zip", "application/x-rar-compressed", "application/x-tar", "application/gzip"]
}

# Default subdirectories for different file types
DEFAULT_SUBDIRECTORIES = {
  "TEXT": "text",
  "IMAGE": "images",
  "AUDIO": "audio",
  "VIDEO": "video",
  "DOCUMENT": "documents",
  "SPREADSHEET": "spreadsheets",
  "PRESENTATION": "presentations",
  "ARCHIVE": "archives",
  "MISC": "misc"
}



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
  - Metadata storage and retrieval

  All classes that deal with file operations should inherit from this class.
  """

  def __init__(self,
               file_path: str,
               base_directory: str,
               file_id: Optional[str] = None,
               file_name: Optional[str] = None,
               mime_type: Optional[str] = None,
               timestamp: Optional[float] = None,
               metadata: Optional[Dict[str, Any]] = None):
    """
    Initialize a BaseFile object.

    Args:
        file_path: The path to the file
        base_directory: The base directory for file operations
        file_id: Optional unique identifier for the file
        file_name: Optional name for the file
        mime_type: Optional MIME type for the file
        timestamp: Optional timestamp for the file
        metadata: Optional metadata for the file
    """
    self.base_directory = base_directory
    self.file_id = file_id or str(uuid.uuid4())
    self.file_path = file_path
    self.file_name = file_name or os.path.basename(file_path)
    self.mime_type = mime_type or mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    self.timestamp = timestamp or time.time()
    self.metadata = metadata or {}

    # Validate that the file exists
    if not os.path.exists(file_path) and os.path.exists(self.get_full_path()):
      self.file_path = self.get_full_path()
    elif not os.path.exists(file_path):
      logger.warning(f"File {file_path} does not exist")

  def get_file_type(self) -> str:
    """
    Get the general type of the file based on its MIME type.

    Returns:
        str: The general type of the file (TEXT, IMAGE, etc.)
    """
    for file_type, mime_types in FILE_TYPES.items():
      if any(self.mime_type.startswith(mime) for mime in mime_types):
        return file_type
    return "MISC"

  def get_subdirectory(self) -> str:
    """
    Get the appropriate subdirectory for this file type.

    Returns:
        str: The subdirectory for this file type
    """
    return DEFAULT_SUBDIRECTORIES.get(self.get_file_type(), DEFAULT_SUBDIRECTORIES["MISC"])

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

  def get_full_path(self) -> str:
    """
    Get the full path for the file.

    Returns:
        str: The full path to the file
    """
    return os.path.join(self.base_directory, self.get_subdirectory(), self.file_id)

  def file_exists(self) -> bool:
    """
    Check if the file exists.

    Returns:
        bool: True if the file exists, False otherwise
    """
    return os.path.exists(self.file_path) or os.path.exists(self.get_full_path())

  def get_file_size(self) -> int:
    """
    Get the size of the file.

    Returns:
        int: The size of the file in bytes, or 0 if the file doesn't exist
    """
    try:
      if os.path.exists(self.file_path):
        return os.path.getsize(self.file_path)
      elif os.path.exists(self.get_full_path()):
        return os.path.getsize(self.get_full_path())
      return 0
    except Exception as e:
      logger.error(f"Failed to get file size for {self.file_path}: {e}")
      return 0

  def copy_to_storage(self) -> bool:
    """
    Copy the file to the storage directory.

    Returns:
        bool: True if the file was copied successfully, False otherwise
    """
    try:
      if not os.path.exists(self.file_path):
        logger.error(f"Source file {self.file_path} does not exist")
        return False

      # Ensure the target directory exists
      target_dir = os.path.join(self.base_directory, self.get_subdirectory())
      os.makedirs(target_dir, exist_ok=True)

      # Copy the file to the target directory with the file_id as the filename
      target_path = self.get_full_path()
      import shutil
      shutil.copy2(self.file_path, target_path)

      # Update the file path to the new location
      self.file_path = target_path
      return True
    except Exception as e:
      logger.error(f"Failed to copy file {self.file_path} to storage: {e}")
      return False

  def save_metadata(self) -> Optional[str]:
    """
    Save the file metadata to a JSON file.

    Returns:
        Optional[str]: The full path to the saved metadata file, or None if saving failed
    """
    try:
      # Ensure the target directory exists
      target_dir = os.path.join(self.base_directory, self.get_subdirectory())
      os.makedirs(target_dir, exist_ok=True)

      # Save the metadata to a JSON file
      metadata_path = f"{self.get_full_path()}.json"
      with open(metadata_path, 'w') as file:
        json.dump(self.to_dict(), file, indent=2)

      return metadata_path
    except Exception as e:
      logger.error(f"Failed to save metadata for {self.file_path}: {e}")
      return None

  def save(self) -> Optional[str]:
    """
    Save the file and its metadata.

    Returns:
        Optional[str]: The full path to the saved file, or None if saving failed
    """
    if not self.copy_to_storage():
      return None

    if not self.save_metadata():
      return None

    return self.get_full_path()

  @classmethod
  def load(cls: Type[T], file_id: str, base_directory: str) -> Optional[T]:
    """
    Load a file from its ID.

    Args:
        file_id: The ID of the file to load
        base_directory: The base directory for file operations

    Returns:
        Optional[T]: The loaded file, or None if loading failed
    """
    try:
      # Try to find the metadata file in each subdirectory
      for subdir in DEFAULT_SUBDIRECTORIES.values():
        metadata_path = os.path.join(base_directory, subdir, f"{file_id}.json")
        if os.path.exists(metadata_path):
          with open(metadata_path, 'r') as file:
            data = json.load(file)

          return cls.from_dict(data, base_directory)

      logger.error(f"Metadata file for {file_id} not found")
      return None
    except Exception as e:
      logger.error(f"Failed to load file {file_id}: {e}")
      return None

  def to_dict(self) -> Dict[str, Any]:
    """
    Convert the file to a dictionary.

    Returns:
        Dict[str, Any]: The file as a dictionary
    """
    return {
      "file_id": self.file_id,
      "file_path": self.file_path,
      "file_name": self.file_name,
      "mime_type": self.mime_type,
      "timestamp": self.timestamp,
      "metadata": self.metadata
    }

  @classmethod
  def from_dict(cls: Type[T], data: Dict[str, Any], base_directory: str) -> T:
    """
    Create a file from a dictionary.

    Args:
        data: The dictionary containing the file data
        base_directory: The base directory for file operations

    Returns:
        T: The created file
    """
    return cls(
      file_path=data["file_path"],
      base_directory=base_directory,
      file_id=data["file_id"],
      file_name=data["file_name"],
      mime_type=data["mime_type"],
      timestamp=data.get("timestamp", time.time()),
      metadata=data.get("metadata", {})
    )

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