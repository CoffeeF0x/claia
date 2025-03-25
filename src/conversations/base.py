"""
This module contains the base file handling functionality for CLAIA.
It defines the base class for file operations used throughout the application.
"""

# TODO:
# - add metadata validation function (such as get image dimensions, get video lenth, verify file exists, etc)
# - add folder validation (loop through each item in subfolder and validate)
# - make metadata a singleton (currently not working)
# - delete should mark a file as deleted in metadata rather than deleting it
# - add a cleanup routine to purge unattached and "deleted" files

# External dependencies
import json
import os
import uuid
import time
import mimetypes
import logging
import shutil
from typing import Dict, List, Any, Optional, Type, TypeVar, Generic, Union, ClassVar



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

# Manifest filename
MANIFEST_FILENAME = "manifest.json"



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)

# Type variable for class methods that return the class instance
T = TypeVar('T', bound='BaseFile')



########################################################################
#                           MANIFEST MANAGER                            #
########################################################################
class ManifestManager:
  """
  Singleton manifest manager that maintains one instance per subdirectory.
  Handles all manifest-related operations for file management.
  """

  # Class variable to store manifest instances for each subdirectory
  _instances: Dict[str, 'ManifestManager'] = {}

  def __init__(self, base_directory: str, subdirectory: str):
    """Private constructor - use get_instance() instead"""
    self.base_directory = base_directory
    self.subdirectory = subdirectory
    self._manifest_data: Dict[str, Dict[str, Any]] = {}
    self._load_manifest()

  @classmethod
  def get_instance(cls, base_directory: str, subdirectory: str) -> 'ManifestManager':
    """
    Get or create a ManifestManager instance for the given subdirectory.

    Args:
        base_directory: Base directory for file operations
        subdirectory: Subdirectory name

    Returns:
        ManifestManager: The singleton instance for this subdirectory
    """
    # Create a unique key for this base_directory + subdirectory combination
    key = f"{base_directory}:{subdirectory}"

    if key not in cls._instances:
      cls._instances[key] = cls(base_directory, subdirectory)

    return cls._instances[key]

  def _get_manifest_path(self) -> str:
    """Get the path to the manifest file."""
    return os.path.join(self.base_directory, self.subdirectory, MANIFEST_FILENAME)

  def _load_manifest(self) -> None:
    """Load the manifest file into memory."""
    manifest_path = self._get_manifest_path()

    if not os.path.exists(manifest_path):
      self._manifest_data = {}
      return

    try:
      with open(manifest_path, 'r') as f:
        self._manifest_data = json.load(f)
    except Exception as e:
      logger.error(f"Failed to load manifest from {manifest_path}: {e}")
      self._manifest_data = {}

  def _save_manifest(self) -> bool:
    """Save the in-memory manifest to file."""
    # Ensure the directory exists
    directory = os.path.join(self.base_directory, self.subdirectory)
    os.makedirs(directory, exist_ok=True)

    manifest_path = self._get_manifest_path()

    try:
      with open(manifest_path, 'w') as f:
        json.dump(self._manifest_data, f, indent=2)
      return True
    except Exception as e:
      logger.error(f"Failed to save manifest to {manifest_path}: {e}")
      return False

  def update_file_metadata(self, file_id: str, metadata: Dict[str, Any]) -> bool:
    """Update metadata for a specific file."""
    self._manifest_data[file_id] = metadata
    return self._save_manifest()

  def remove_file_metadata(self, file_id: str) -> bool:
    """Remove metadata for a specific file."""
    if file_id in self._manifest_data:
      del self._manifest_data[file_id]
      return self._save_manifest()
    return True

  def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
    """Get metadata for a specific file."""
    return self._manifest_data.get(file_id)

  def get_all_files(self) -> Dict[str, Dict[str, Any]]:
    """Get all file metadata in this manifest."""
    return self._manifest_data.copy()

  @classmethod
  def find_file_metadata(cls, base_directory: str, file_id: str) -> Optional[tuple[Dict[str, Any], str]]:
    """Find metadata for a file in any subdirectory."""
    for subdir in DEFAULT_SUBDIRECTORIES.values():
      manager = cls.get_instance(base_directory, subdir)
      metadata = manager.get_file_metadata(file_id)
      if metadata:
        return metadata, subdir
    return None



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

  # Add class variable for manifest manager
  _manifest_manager: ClassVar[Optional[ManifestManager]] = None

  def __init__(self,
               base_directory: str,
               file_name: Optional[str] = None,
               mime_type: Optional[str] = None):
    """
    Initialize a BaseFile object.

    Args:
        base_directory: The base directory for file
        file_name: Optional, specify the name for the file
        mime_type: Optional, specify MIME type for the file
    """
    self.base_directory = base_directory
    self.file_id = str(uuid.uuid4())
    self.file_name = file_name or self.file_id
    self.file_path = os.path.join(self.base_directory, self.file_name)
    self.mime_type = mime_type or mimetypes.guess_type(self.file_path)[0] or "application/octet-stream"
    self.timestamp = time.time()
    self.metadata = {}

    logger.debug(f"Initializing new file ({self.file_id})")
    logger.debug(f"base directory ({self.file_id}): {self.base_directory}")
    logger.debug(f"file name ({self.file_id}): {self.file_name}")
    logger.debug(f"file path ({self.file_id}): {self.file_path}")
    logger.debug(f"mime type ({self.file_id}): {self.mime_type}")

    # Validate that the file exists
    if not os.path.exists(self.file_path) and os.path.exists(self.get_full_path()):
      self.file_path = self.get_full_path()
    elif not os.path.exists(self.file_path):
      logger.warning(f"File {self.file_path} does not exist")

    # Initialize manifest manager if not already initialized
    if BaseFile._manifest_manager is None:
      BaseFile._manifest_manager = ManifestManager(base_directory, DEFAULT_SUBDIRECTORIES[self.get_file_type()])

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
    Ensure that the base directory and subdirectory exist.

    Returns:
        bool: True if the directories exist or were created, False otherwise
    """
    try:
      # Create base directory if it doesn't exist
      if not os.path.exists(self.base_directory):
        logger.debug(f"Base directory doesn't exist, creating directory (file: {self.file_id})")
        os.makedirs(self.base_directory, exist_ok=True)

      # Create subdirectory if it doesn't exist
      subdir_path = os.path.join(self.base_directory, self.get_subdirectory())
      if not os.path.exists(subdir_path):
        logger.debug(f"Subdirectory doesn't exist, creating directory (file: {self.file_id})")
        os.makedirs(subdir_path, exist_ok=True)

      return True
    except Exception as e:
      logger.error(f"Failed to create directories {self.base_directory}: {e}")
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
      if not self.ensure_directory_exists():
        return False

      # Copy the file to the target directory with the file_id as the filename
      target_path = self.get_full_path()
      shutil.copy2(self.file_path, target_path)

      # Update the file path to the new location
      self.file_path = target_path
      return True
    except Exception as e:
      logger.error(f"Failed to copy file {self.file_path} to storage: {e}")
      return False

  def save_metadata(self) -> Optional[str]:
    """
    Save the file metadata to the manifest file.

    Returns:
        Optional[str]: The full path to the manifest file, or None if saving failed
    """
    try:
      subdirectory = self.get_subdirectory()
      
      if not self.ensure_directory_exists():
        return None

      # Get the manifest manager for this subdirectory
      manager = ManifestManager.get_instance(self.base_directory, subdirectory)
      
      if manager.update_file_metadata(self.file_id, self.to_dict()):
        return manager._get_manifest_path()
      return None
    except Exception as e:
      logger.error(f"Failed to save metadata for {self.file_path}: {e}")
      return None

  def save(self) -> Optional[str]:
    """
    Save the file and its metadata.

    Returns:
        Optional[str]: The full path to the saved file, or None if saving failed
    """
    # Ensure the directory exists before saving
    if not self.ensure_directory_exists():
      return None

    if not self.copy_to_storage():
      logger.debug(f"Failed to save file {self.file_id}")
      return None

    if not self.save_metadata():
      logger.debug(f"Failed to save metadata for file {self.file_id}")
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
      result = ManifestManager.find_file_metadata(base_directory, file_id)
      if result:
        data, _ = result
        return cls.from_dict(data, base_directory)
      # TODO:
      # If metadata not found, then create a metadata: None or something in the manifest

      logger.error(f"File {file_id} not found in any manifest")
      return None
    except Exception as e:
      logger.error(f"Failed to load file {file_id}: {e}")
      return None

  @classmethod
  def delete(cls, file_id: str, base_directory: str) -> bool:
    """
    Delete a file and its metadata.

    Args:
        file_id: The ID of the file to delete
        base_directory: The base directory for file operations

    Returns:
        bool: True if deletion succeeded, False otherwise
    """
    try:
      if cls._manifest_manager is None:
        cls._manifest_manager = ManifestManager(base_directory, DEFAULT_SUBDIRECTORIES[cls.get_file_type()])

      result = cls._manifest_manager.find_file_metadata(base_directory, file_id)
      if result:
        _, subdir = result
        file_path = os.path.join(base_directory, subdir, file_id)

        # Delete the file if it exists
        try:
          if os.path.exists(file_path):
            os.remove(file_path)
        except Exception as e:
          logger.error(f"Failed to delete file {file_path}: {e}")
          return False

        # Remove from manifest
        return cls._manifest_manager.remove_file_metadata(file_id)

      logger.warning(f"File {file_id} not found in any manifest")
      return False
    except Exception as e:
      logger.error(f"Failed to delete file {file_id}: {e}")
      return False

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

  @classmethod
  def list_files(cls, base_directory: str, subdirectory: str = None) -> List[Dict[str, Any]]:
    """
    List all files in a directory with metadata from the manifest.

    Args:
        base_directory: The base directory for file operations
        subdirectory: Optional specific subdirectory to list files from

    Returns:
        List[Dict[str, Any]]: A list of file metadata
    """
    files = []

    try:
      # If a specific subdirectory is provided, only check that one
      subdirs = [subdirectory] if subdirectory else DEFAULT_SUBDIRECTORIES.values()

      for subdir in subdirs:
        manager = ManifestManager.get_instance(base_directory, subdir)
        manifest = manager.get_all_files()

        # Add each file's metadata to the list
        for file_id, data in manifest.items():
          files.append({
            "file_id": file_id,
            "file_name": data.get("file_name", ""),
            "mime_type": data.get("mime_type", ""),
            "timestamp": data.get("timestamp", 0),
            "subdirectory": subdir
          })

      # Sort by timestamp, newest first
      files.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
      return files
    except Exception as e:
      logger.error(f"Failed to list files: {e}")
      return []
