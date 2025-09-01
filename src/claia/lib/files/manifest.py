"""
This module contains the file manifest functionality for CLAIA.
It defines the FileManifest singleton for centralized file metadata management.
"""

# External dependencies
import json
import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

# Internal dependencies
from ..enums.file import FileStatus



########################################################################
#                              CONSTANTS                               #
########################################################################
MANIFEST_FILENAME = "manifest.json"



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                             FILEMANIFEST                             #
########################################################################
class FileManifest:
  """
  Singleton class that manages file metadata across all subdirectories.
  Provides a centralized repository for tracking files, their references,
  and deletion status.
  """

  _instance = None

  def __new__(cls, base_directory: str):
    if cls._instance is None:
      cls._instance = super(FileManifest, cls).__new__(cls)
      cls._instance._initialized = False
    return cls._instance

  def __init__(self, base_directory: str):
    if self._initialized:
      return

    self.base_directory = base_directory
    self._manifest_data: Dict[str, Dict[str, Any]] = {}
    self._load_manifest()
    self._initialized = True

  def _get_manifest_path(self) -> str:
    """Get the path to the manifest file."""
    return os.path.join(self.base_directory, MANIFEST_FILENAME)

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
    os.makedirs(self.base_directory, exist_ok=True)

    manifest_path = self._get_manifest_path()

    try:
      with open(manifest_path, 'w') as f:
        json.dump(self._manifest_data, f, indent=2)
      return True
    except Exception as e:
      logger.error(f"Failed to save manifest to {manifest_path}: {e}")
      return False

  def add(self, file_obj) -> bool:
    """
    Add a BaseFile object to the manifest.

    Args:
      file_obj: BaseFile object or child class instance

    Returns:
      bool: True if successful, False otherwise
    """
    if not hasattr(file_obj, 'file_id') or not hasattr(file_obj, 'to_dict'):
      logger.error(f"Invalid file object passed to add(): missing file_id or to_dict method")
      return False

    logger.debug(f"Adding file to manifest: {file_obj.file_id} (type: {type(file_obj).__name__})")
    self._manifest_data[file_obj.file_id] = file_obj.to_dict()

    if self._save_manifest():
      logger.info(f"Successfully added file to manifest: {file_obj.file_id}")
      return True
    else:
      logger.error(f"Failed to save manifest after adding file: {file_obj.file_id}")
      return False

  def update(self, file_obj) -> bool:
    """
    Update a BaseFile object's metadata in the manifest.

    Args:
      file_obj: BaseFile object or child class instance

    Returns:
      bool: True if successful, False otherwise
    """
    if not hasattr(file_obj, 'file_id') or not hasattr(file_obj, 'to_dict'):
      logger.error(f"Invalid file object passed to update(): missing file_id or to_dict method")
      return False

    if file_obj.file_id not in self._manifest_data:
      logger.warning(f"Attempted to update non-existent file: {file_obj.file_id}")
      return False

    logger.debug(f"Updating file in manifest: {file_obj.file_id} (type: {type(file_obj).__name__})")
    self._manifest_data[file_obj.file_id] = file_obj.to_dict()

    if self._save_manifest():
      logger.debug(f"Successfully updated file in manifest: {file_obj.file_id}")
      return True
    else:
      logger.error(f"Failed to save manifest after updating file: {file_obj.file_id}")
      return False

  def remove(self, file_obj) -> bool:
    """
    Remove a BaseFile object from the manifest.

    Args:
      file_obj: BaseFile object or child class instance

    Returns:
      bool: True if successful, False otherwise
    """
    if not hasattr(file_obj, 'file_id'):
      logger.error(f"Invalid file object passed to remove(): missing file_id")
      return False

    if file_obj.file_id in self._manifest_data:
      logger.debug(f"Removing file from manifest: {file_obj.file_id}")
      del self._manifest_data[file_obj.file_id]

      if self._save_manifest():
        logger.info(f"Successfully removed file from manifest: {file_obj.file_id}")
        return True
      else:
        logger.error(f"Failed to save manifest after removing file: {file_obj.file_id}")
        return False
    else:
      logger.debug(f"File not found in manifest for removal: {file_obj.file_id}")
      return True

  def save(self, file_obj) -> bool:
    """
    Save a BaseFile object to the manifest (update if exists, add if new).

    Args:
      file_obj: BaseFile object or child class instance

    Returns:
      bool: True if successful, False otherwise
    """
    if not hasattr(file_obj, 'file_id') or not hasattr(file_obj, 'to_dict'):
      logger.error(f"Invalid file object passed to save(): missing file_id or to_dict method")
      return False

    # Try to update first, if file doesn't exist, add it
    if file_obj.file_id in self._manifest_data:
      logger.debug(f"File exists in manifest, updating: {file_obj.file_id}")
      return self.update(file_obj)
    else:
      logger.debug(f"File not in manifest, adding: {file_obj.file_id}")
      return self.add(file_obj)

  def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
    """Get metadata for a specific file."""
    return self._manifest_data.get(file_id)

  def get_all_files(self) -> Dict[str, Dict[str, Any]]:
    """Get all file metadata."""
    return self._manifest_data.copy()

  def get_files_by_status(self, status: FileStatus) -> List[str]:
    """Get all file IDs with the specified status."""
    return [
      file_id for file_id, metadata in self._manifest_data.items()
      if metadata.get("status") == status.name
    ]

  def delete(self, file_obj) -> bool:
    """
    Delete a BaseFile object (marks it for deletion in manifest).

    Args:
      file_obj: BaseFile object or child class instance

    Returns:
      bool: True if successful, False otherwise
    """
    if not hasattr(file_obj, 'file_id'):
      logger.error(f"Invalid file object passed to delete(): missing file_id")
      return False

    if file_obj.file_id not in self._manifest_data:
      logger.warning(f"Attempted to delete non-existent file: {file_obj.file_id}")
      return False

    logger.info(f"Marking file for deletion: {file_obj.file_id}")
    self._manifest_data[file_obj.file_id]["status"] = FileStatus.DELETED.name
    self._manifest_data[file_obj.file_id]["deletion_timestamp"] = datetime.now().isoformat()

    if self._save_manifest():
      logger.info(f"Successfully marked file for deletion: {file_obj.file_id}")
      return True
    else:
      logger.error(f"Failed to save manifest after marking file for deletion: {file_obj.file_id}")
      return False

  def get_unreferenced_files(self) -> List[str]:
    """
    Get all file IDs that have no references.

    Returns:
      List[str]: List of file IDs with no references
    """
    return [
      file_id for file_id, metadata in self._manifest_data.items()
      if not metadata.get("references") and metadata.get("status") == FileStatus.ACTIVE.name
    ]

  def cleanup_files(self, older_than_days: int = 30) -> List[str]:
    """
    Find files marked for deletion that are older than specified days.

    Args:
      older_than_days: Only include files deleted more than this many days ago

    Returns:
      List[str]: List of file IDs ready for permanent deletion
    """
    now = datetime.now()
    cleanup_list = []

    for file_id, metadata in self._manifest_data.items():
      if metadata.get("status") != FileStatus.DELETED.name:
        continue

      if "deletion_timestamp" not in metadata:
        cleanup_list.append(file_id)
        continue

      try:
        deletion_time = datetime.fromisoformat(metadata["deletion_timestamp"])
        days_since_deletion = (now - deletion_time).days

        if days_since_deletion >= older_than_days:
          cleanup_list.append(file_id)
      except Exception as e:
        logger.error(f"Error parsing deletion timestamp for {file_id}: {e}")

    return cleanup_list

  def permanently_delete_files(self, older_than_days: int = 30) -> int:
    """
    Permanently delete files marked for deletion.

    Args:
      older_than_days: Only delete files marked for deletion older than this many days

    Returns:
      int: Number of files actually deleted
    """
    logger.info(f"Starting permanent deletion of files older than {older_than_days} days")
    cleanup_list = self.cleanup_files(older_than_days)
    deleted_count = 0

    logger.debug(f"Found {len(cleanup_list)} files marked for cleanup")

    for file_id in cleanup_list:
      file_data = self._manifest_data.get(file_id)
      if not file_data:
        logger.warning(f"File data not found for cleanup file: {file_id}")
        continue

      # Only delete if the file has no references
      if not file_data.get("references"):
        file_path = os.path.join(self.base_directory, file_data.get("subdirectory", ""), file_data.get("file_name"))

        try:
          if os.path.exists(file_path):
            os.remove(file_path)
            logger.debug(f"Deleted file from disk: {file_path}")
            deleted_count += 1
          else:
            logger.debug(f"File already missing from disk: {file_path}")
        except Exception as e:
          logger.error(f"Failed to delete file {file_path}: {e}")
          continue

        # Remove from manifest
        self._remove_file_metadata_by_id(file_id)
        logger.debug(f"Removed file from manifest: {file_id}")
      else:
        logger.debug(f"Skipping file with references: {file_id}")

    logger.info(f"Permanently deleted {deleted_count} files")
    return deleted_count

  def _remove_file_metadata_by_id(self, file_id: str) -> bool:
    """
    Private helper method to remove metadata by file_id.
    Used internally by cleanup operations.

    Args:
      file_id: ID of the file to remove

    Returns:
      bool: True if successful, False otherwise
    """
    if file_id in self._manifest_data:
      del self._manifest_data[file_id]
      return self._save_manifest()
    return True

  def find_files_by_criteria(self,
                             subdirectory: Optional[str] = None,
                             metadata_filters: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    """
    Find files that match specific criteria.

    This method searches through the file manifest and returns all files that match
    the specified subdirectory and/or metadata filters.

    Args:
      subdirectory: Optional subdirectory to filter by
      metadata_filters: Optional dictionary with metadata keys and values to match

    Returns:
      Dict[str, Dict[str, Any]]: Dictionary of file_id -> metadata for matching files
    """
    logger.debug(f"Searching files with criteria - subdirectory: {subdirectory}, filters: {metadata_filters}")
    all_files = self.get_all_files()
    matching_files = {}

    # Filter files based on criteria
    for file_id, metadata in all_files.items():
      # Skip deleted files unless specifically looking for them
      if metadata.get('status') == FileStatus.DELETED.name:
        if not metadata_filters or metadata_filters.get('status') != FileStatus.DELETED.name:
          continue

      # If subdirectory is specified, check if it matches
      if subdirectory and metadata.get("subdirectory") != subdirectory:
        continue

      # If metadata filters are specified, check if all criteria match
      if metadata_filters:
        match = True
        for key, value in metadata_filters.items():
          # For nested metadata keys (e.g., "metadata.prompt_name")
          if "." in key:
            parts = key.split(".")
            current = metadata
            for part in parts:
              if part in current:
                current = current[part]
              else:
                match = False
                break
            # If we got all the way through the parts but the value doesn't match
            if match and current != value:
              match = False
          # For top-level metadata keys
          elif key not in metadata or metadata[key] != value:
            match = False
            break

        if not match:
          continue

      matching_files[file_id] = metadata

    logger.debug(f"Found {len(matching_files)} files matching criteria")
    return matching_files
