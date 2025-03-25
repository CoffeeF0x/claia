"""
This module contains the refactored base file handling functionality for CLAIA.
It defines the BaseFile class for file operations.
"""

# External dependencies
import os
import uuid
import time
import mimetypes
import logging
import shutil
from typing import Dict, List, Any, Optional, Type, TypeVar, Union
from datetime import datetime

# Internal dependencies
from enums import FileSubdirectory, FileStatus
from .manifest import FileManifest, MANIFEST_FILENAME



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)

# Type variable for class methods that return the class instance
T = TypeVar('T', bound='BaseFile')



########################################################################
#                              BASEFILE                                #
########################################################################
class BaseFile:
  """
  Base class for all file operations in CLAIA.
  
  This class provides common functionality for file operations such as:
  - Directory creation and validation
  - File saving and loading
  - Support for external file references
  - Metadata storage and retrieval
  - File status tracking
  
  All classes that deal with file operations should inherit from this class.
  """
  
  def __init__(self,
               base_directory: str,
               file_name: Optional[str] = None,
               external_path: Optional[str] = None,
               is_reference: bool = False,
               file_id: Optional[str] = None,
               mime_type: Optional[str] = None,
               timestamp: Optional[float] = None,
               metadata: Optional[Dict[str, Any]] = None):
    """
    Initialize a BaseFile object.
    
    Args:
      base_directory: Base directory for file storage
      file_name: Optional name for the file
      external_path: Optional path or URL to an external file
      is_reference: Whether to store only a reference to the file
      file_id: Optional ID for the file (generated if not provided)
      mime_type: Optional MIME type (detected if not provided)
      timestamp: Optional timestamp (current time if not provided)
      metadata: Optional additional metadata for the file
    """
    self.base_directory = base_directory
    self.file_id = file_id or str(uuid.uuid4())
    self.file_name = file_name or self.file_id
    self.external_path = external_path
    self.is_reference = is_reference
    self.timestamp = timestamp or time.time()
    self.metadata = metadata or {}
    
    # Determine MIME type
    if mime_type:
      self.mime_type = mime_type
    elif external_path:
      self.mime_type = mimetypes.guess_type(external_path)[0] or "application/octet-stream"
    else:
      self.mime_type = mimetypes.guess_type(self.file_name)[0] or "application/octet-stream"
    
    # Set file path based on source (external or internal)
    if external_path and os.path.exists(external_path) and is_reference:
      self.file_path = external_path
      self.status = FileStatus.EXTERNAL
    else:
      self.file_path = self.get_full_path()
      self.status = FileStatus.ACTIVE
    
    # Initialize manifest
    self.manifest = FileManifest(base_directory)
    
    logger.debug(f"Initializing file: id={self.file_id}, name={self.file_name}, reference={is_reference}")
  
  def get_file_type(self) -> FileSubdirectory:
    """Get the file type enum based on MIME type."""
    return FileSubdirectory.from_mime_type(self.mime_type)
  
  def get_subdirectory(self) -> str:
    """Get the appropriate subdirectory for this file type."""
    return self.get_file_type().value
  
  def ensure_directory_exists(self) -> bool:
    """
    Ensure that the necessary directories exist.
    
    Returns:
      bool: True if the directories exist or were created
    """
    try:
      # Create base directory if it doesn't exist
      if not os.path.exists(self.base_directory):
        os.makedirs(self.base_directory, exist_ok=True)
      
      # Create subdirectory if it doesn't exist
      subdir_path = os.path.join(self.base_directory, self.get_subdirectory())
      if not os.path.exists(subdir_path):
        os.makedirs(subdir_path, exist_ok=True)
          
      return True
    except Exception as e:
      logger.error(f"Failed to create directories for {self.file_id}: {e}")
      return False
  
  def get_full_path(self) -> str:
    """Get the full path for the file."""
    return os.path.join(self.base_directory, self.get_subdirectory(), self.file_id)
  
  def file_exists(self) -> bool:
    """Check if the file exists."""
    if self.is_reference and self.external_path:
      return os.path.exists(self.external_path)
    return os.path.exists(self.file_path)
  
  def get_file_size(self) -> int:
    """Get the size of the file in bytes."""
    try:
      if self.file_exists():
        return os.path.getsize(self.file_path)
      return 0
    except Exception as e:
      logger.error(f"Failed to get file size for {self.file_path}: {e}")
      return 0
  
  def copy_to_storage(self) -> bool:
    """
    Copy the file to the storage directory.
    
    Returns:
      bool: True if the file was copied successfully
    """
    # If this is a reference-only file, don't copy
    if self.is_reference:
      return True
        
    try:
      # If external path exists, copy from there
      if self.external_path and os.path.exists(self.external_path):
        source_path = self.external_path
      elif os.path.exists(self.file_path):
        source_path = self.file_path
      else:
        logger.error(f"No source file found for {self.file_id}")
        return False
      
      # Ensure the target directory exists
      if not self.ensure_directory_exists():
        return False
      
      # Copy the file with the file_id as the filename
      target_path = self.get_full_path()
      shutil.copy2(source_path, target_path)
      
      # Update the file path to the new location
      self.file_path = target_path
      return True
    except Exception as e:
      logger.error(f"Failed to copy file {self.file_id} to storage: {e}")
      return False
  
  def to_dict(self) -> Dict[str, Any]:
    """Convert the file to a dictionary."""
    return {
      "file_id": self.file_id,
      "file_name": self.file_name,
      "file_path": self.file_path,
      "external_path": self.external_path,
      "is_reference": self.is_reference,
      "mime_type": self.mime_type,
      "timestamp": self.timestamp,
      "status": self.status.name,
      "subdirectory": self.get_subdirectory(),
      "metadata": self.metadata,
      "references": []  # Will be populated from manifest when saved
    }
  
  def save_metadata(self) -> bool:
    """
    Save the file metadata to the manifest.
    
    Returns:
      bool: True if metadata was saved successfully
    """
    return self.manifest.update_file_metadata(self.file_id, self.to_dict())
  
  def save(self) -> Optional[str]:
    """
    Save the file and its metadata.
    
    Returns:
      Optional[str]: The full path to the saved file, or None if saving failed
    """
    # Ensure the directory exists
    if not self.ensure_directory_exists():
      return None
    
    # If not a reference, copy the file to storage
    if not self.is_reference and not self.copy_to_storage():
      logger.error(f"Failed to save file {self.file_id}")
      return None
    
    # Save metadata regardless of whether it's a reference
    if not self.save_metadata():
      logger.error(f"Failed to save metadata for file {self.file_id}")
      return None
    
    return self.file_path
  
  def mark_for_deletion(self) -> bool:
    """
    Mark the file for deletion instead of deleting immediately.
    
    Returns:
      bool: True if the file was marked for deletion
    """
    self.status = FileStatus.DELETED
    return self.manifest.mark_for_deletion(self.file_id)
  
  def add_reference(self, reference_id: str) -> bool:
    """
    Add a reference to this file.
    
    Args:
      reference_id: ID of the object referencing this file
        
    Returns:
      bool: True if successful
    """
    return self.manifest.add_reference(self.file_id, reference_id)
  
  def remove_reference(self, reference_id: str) -> bool:
    """
    Remove a reference to this file.
    
    Args:
      reference_id: ID of the object that was referencing this file
        
    Returns:
      bool: True if successful
    """
    return self.manifest.remove_reference(self.file_id, reference_id)
  
  def export(self, target_path: str, force_overwrite: bool = False) -> bool:
    """
    Export the file to an external path.
    
    This method allows exporting a stored file to a path outside the
    file system. For reference files, it will export the referenced file
    if it exists.
    
    Args:
      target_path: Path where the file should be exported
      force_overwrite: Whether to overwrite the file if it already exists
      
    Returns:
      bool: True if the file was exported successfully, False otherwise
    """
    # Check if the file exists in our system
    if not self.file_exists():
      logger.error(f"Cannot export non-existent file: {self.file_id}")
      return False
    
    # Check if target already exists
    if os.path.exists(target_path) and not force_overwrite:
      logger.error(f"Target path already exists and force_overwrite is False: {target_path}")
      return False
    
    try:
      # Create target directory if it doesn't exist
      target_dir = os.path.dirname(target_path)
      if target_dir and not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)
      
      # Copy the file to the target path
      source_path = self.file_path
      shutil.copy2(source_path, target_path)
      
      logger.debug(f"Exported file {self.file_id} to {target_path}")
      return True
    except Exception as e:
      logger.error(f"Failed to export file {self.file_id} to {target_path}: {e}")
      return False
  
  @classmethod
  def load(cls: Type[T], file_id: str, base_directory: str) -> Optional[T]:
    """
    Load a file from its ID.
    
    Args:
      file_id: The ID of the file to load
      base_directory: The base directory for file operations
        
    Returns:
      Optional[T]: The loaded file object, or None if loading failed
    """
    manifest = FileManifest(base_directory)
    metadata = manifest.get_file_metadata(file_id)
    
    if not metadata:
      logger.error(f"File {file_id} not found in manifest")
      return None
    
    try:
      # Create instance with data from manifest
      return cls(
        base_directory=base_directory,
        file_name=metadata.get("file_name"),
        external_path=metadata.get("external_path"),
        is_reference=metadata.get("is_reference", False),
        file_id=file_id,
        mime_type=metadata.get("mime_type"),
        timestamp=metadata.get("timestamp"),
        metadata=metadata.get("metadata", {})
      )
    except Exception as e:
      logger.error(f"Failed to load file {file_id}: {e}")
      return None
  
  @classmethod
  def from_path(cls: Type[T], path: str, base_directory: str, 
                is_reference: bool = False) -> Optional[T]:
    """
    Create a file object from a local file path.
    
    Args:
      path: Path to the local file
      base_directory: Base directory for file operations
      is_reference: Whether to store only a reference to the file
        
    Returns:
      Optional[T]: The created file object, or None if creation failed
    """
    if not os.path.exists(path):
      logger.error(f"File {path} does not exist")
      return None
        
    try:
      return cls(
        base_directory=base_directory,
        file_name=os.path.basename(path),
        external_path=path,
        is_reference=is_reference
      )
    except Exception as e:
      logger.error(f"Failed to create file from path {path}: {e}")
      return None
  
  @classmethod
  def from_url(cls: Type[T], url: str, base_directory: str, 
              is_reference: bool = True) -> Optional[T]:
    """
    Create a file object from a URL.
    
    Args:
      url: URL to the remote file
      base_directory: Base directory for file operations
      is_reference: Whether to store only a reference (usually True for URLs)
        
    Returns:
      Optional[T]: The created file object, or None if creation failed
    """
    try:
      return cls(
        base_directory=base_directory,
        file_name=os.path.basename(url) or "url_file",
        external_path=url,
        is_reference=is_reference
      )
    except Exception as e:
      logger.error(f"Failed to create file from URL {url}: {e}")
      return None
  
  @classmethod
  def cleanup_deleted_files(cls, base_directory: str, older_than_days: int = 30) -> int:
    """
    Permanently delete files that were marked for deletion.
    
    Args:
      base_directory: Base directory for file operations
      older_than_days: Only delete files deleted this many days ago
        
    Returns:
      int: Number of files deleted
    """
    manifest = FileManifest(base_directory)
    cleanup_list = manifest.cleanup_files(older_than_days)
    deleted_count = 0
    
    for file_id in cleanup_list:
      metadata = manifest.get_file_metadata(file_id)
      if not metadata:
        continue
          
      # Only try to delete if it's not a reference
      if not metadata.get("is_reference", False):
        subdirectory = metadata.get("subdirectory", "misc")
        file_path = os.path.join(base_directory, subdirectory, file_id)
        
        if os.path.exists(file_path):
          try:
            os.remove(file_path)
            deleted_count += 1
          except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            continue
      
      # Remove from manifest regardless of whether file deletion succeeded
      manifest.remove_file_metadata(file_id)
    
    return deleted_count