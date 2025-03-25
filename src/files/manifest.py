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
from enums import FileStatus



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
    """Get all file metadata."""
    return self._manifest_data.copy()
  
  def get_files_by_status(self, status: FileStatus) -> List[str]:
    """Get all file IDs with the specified status."""
    return [
      file_id for file_id, metadata in self._manifest_data.items()
      if metadata.get("status") == status.name
    ]
  
  def add_reference(self, file_id: str, reference_id: str) -> bool:
    """
    Add a reference to a file.
    
    Args:
      file_id: ID of the file being referenced
      reference_id: ID of the object referencing this file
      
    Returns:
      bool: True if successful, False otherwise
    """
    if file_id not in self._manifest_data:
      return False
    
    # Make sure references is initialized
    if "references" not in self._manifest_data[file_id]:
      self._manifest_data[file_id]["references"] = []
    
    # Add reference if not already present
    references = self._manifest_data[file_id]["references"]
    if reference_id not in references:
      references.append(reference_id)
      return self._save_manifest()
      
    return True
  
  def remove_reference(self, file_id: str, reference_id: str) -> bool:
    """
    Remove a reference from a file.
    
    Args:
      file_id: ID of the file being referenced
      reference_id: ID of the object that was referencing this file
      
    Returns:
      bool: True if successful, False otherwise
    """
    if file_id not in self._manifest_data:
      return False
      
    if "references" not in self._manifest_data[file_id]:
      return True  # Nothing to remove
    
    references = self._manifest_data[file_id]["references"]
    if reference_id in references:
      references.remove(reference_id)
      return self._save_manifest()
      
    return True
  
  def mark_for_deletion(self, file_id: str) -> bool:
    """
    Mark a file for deletion.
    
    Args:
      file_id: ID of the file to mark for deletion
      
    Returns:
      bool: True if successful, False otherwise
    """
    if file_id not in self._manifest_data:
      return False
    
    self._manifest_data[file_id]["status"] = FileStatus.DELETED.name
    self._manifest_data[file_id]["deletion_timestamp"] = datetime.now().isoformat()
    return self._save_manifest()
  
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