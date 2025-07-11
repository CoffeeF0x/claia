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
from typing import Dict, Any, Optional, Type, TypeVar, Union

# Internal dependencies
from ..enums.file import FileSubdirectory, FileStatus, FileMimeType
from .manifest import FileManifest



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
               source_path: Optional[str] = None,
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
      source_path: Optional original path or URL to the file
      is_reference: Whether to store only a reference to the file
      file_id: Optional ID for the file (generated if not provided)
      mime_type: Optional MIME type (detected if not provided)
      timestamp: Optional timestamp (current time if not provided)
      metadata: Optional additional metadata for the file
    """
    self.base_directory = base_directory
    self.file_id = file_id or str(uuid.uuid4())
    self.file_name = file_name or self.file_id
    self.is_reference = is_reference
    self.timestamp = timestamp or time.time()
    self.metadata = metadata or {}

    # Determine MIME type
    if mime_type:
      self.mime_type = mime_type
    elif source_path:
      self.mime_type = mimetypes.guess_type(source_path)[0] or "application/octet-stream"
    else:
      self.mime_type = mimetypes.guess_type(self.file_name)[0] or "application/octet-stream"

    # Store original source path in metadata
    if source_path:
      self.metadata["source_path"] = source_path

    # Set file path based on reference mode
    if is_reference and source_path and (self._is_url(source_path) or os.path.exists(source_path)):
      self.path = source_path
      self.status = FileStatus.EXTERNAL
    else:
      self.path = self.get_internal_path()
      self.status = FileStatus.ACTIVE

    # Initialize manifest
    self.manifest = FileManifest(base_directory)

    logger.debug(f"Initializing file: id={self.file_id}, name={self.file_name}, reference={is_reference}")

  def get_file_type(self) -> FileSubdirectory:
    """Get the file type enum based on MIME type."""
    return FileSubdirectory.from_mime_type(self.mime_type)

  def get_subdirectory(self) -> str:
    """Get the appropriate subdirectory for this file type."""
    # Check if there's an override subdirectory specified
    if hasattr(self, '_override_subdirectory') and self._override_subdirectory:
      return self._override_subdirectory
    # Fall back to the file type based on mime type
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

  def get_internal_path(self) -> str:
    """Get the full path for the file in internal storage."""
    return os.path.join(self.base_directory, self.get_subdirectory(), self.file_id)

  def get_source_path(self) -> Optional[str]:
    """Get the original source path of the file."""
    return self.metadata.get("source_path")

  def exists(self) -> bool:
    """
    Check if the file or resource exists.

    This method handles different types of files and resources:
    - For URL references: Checks if the URL is accessible
    - For file references: Checks if the referenced file exists
    - For internal files: Checks if the file exists in storage

    Returns:
      bool: True if the file or resource exists, False otherwise
    """
    # Check if this is a URL reference
    if self.is_reference and self._is_url(self.path):
      return self._url_exists(self.path)

    # For regular files and local references, check if file exists
    return os.path.exists(self.path)

  def get_file_size(self) -> int:
    """Get the size of the file in bytes."""
    try:
      if self.exists():
        return os.path.getsize(self.path)
      return 0
    except Exception as e:
      logger.error(f"Failed to get file size for {self.path}: {e}")
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
      # Get source path (either original source or current path)
      source_path = self.get_source_path()
      if source_path and os.path.exists(source_path):
        source = source_path
      elif os.path.exists(self.path):
        source = self.path
      else:
        logger.error(f"No source file found for {self.file_id}")
        return False

      # Ensure the target directory exists
      if not self.ensure_directory_exists():
        return False

      # Copy the file with the file_id as the filename
      target_path = self.get_internal_path()
      shutil.copy2(source, target_path)

      # Update the file path to the new location
      self.path = target_path
      return True
    except Exception as e:
      logger.error(f"Failed to copy file {self.file_id} to storage: {e}")
      return False

  def to_dict(self) -> Dict[str, Any]:
    """Convert the file to a dictionary."""
    return {
      "file_id": self.file_id,
      "file_name": self.file_name,
      "path": self.path,
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

  def _write_content_to_file(self, full_path: str, content: Union[str, bytes], encoding: str = "utf-8") -> bool:
    """
    Write content to a file at the specified path.

    Args:
      full_path: Path to write the content to
      content: Content to write (string or bytes)
      encoding: Encoding to use for string content

    Returns:
      bool: True if writing was successful, False otherwise
    """
    try:
      # Determine the write mode based on content type
      mode = "wb" if isinstance(content, bytes) else "w"

      if mode == "wb":
        with open(full_path, mode) as f:
          f.write(content)
      else:
        with open(full_path, mode, encoding=encoding) as f:
          f.write(content)

      # If this is a TextFile instance and we're writing string content,
      # update encoding if needed
      if hasattr(self, 'encoding') and encoding and isinstance(content, str):
        self.encoding = encoding
        if 'encoding' in self.metadata:
          self.metadata['encoding'] = encoding

      return True
    except Exception as e:
      logger.error(f"Failed to write content to file {self.file_id}: {e}")
      return False

  def _update_metadata(self):
    """
    Hook method called before saving metadata.

    This should be overridden by subclasses to ensure the self.metadata
    dictionary is up-to-date with any class-specific information
    before it's written to the manifest by save_metadata().

    The default implementation does nothing.
    """
    pass

  def _get_default_content(self) -> Optional[Union[str, bytes]]:
    """
    Hook method to provide default content when saving without content.

    This can be overridden by subclasses to provide default content
    when no content is provided to the save method. For example,
    JSON-based files can serialize their data to JSON.

    Returns:
      Optional[Union[str, bytes]]: Default content to save, or None if no default
    """
    return None

  def save(self, content: Optional[Union[str, bytes]] = None, encoding: str = "utf-8") -> Optional[str]:
    """
    Save the file and its metadata.

    This method can also be used to update the content of an existing file
    by passing the new content as a parameter.

    When content is provided for a reference file, it will automatically
    convert the file to a local file.

    Args:
      content: Optional content to write to the file (string or bytes)
      encoding: Encoding to use when writing string content (default: utf-8)

    Returns:
      Optional[str]: The full path to the saved file, or None if saving failed
    """
    # Ensure the directory exists
    if not self.ensure_directory_exists():
      return None

    # If content is not provided, get default content from hook
    if content is None:
      content = self._get_default_content()

    # If content is provided or generated by the hook, write it
    if content is not None:
      # For reference files, we need to update path and status
      if self.is_reference:
        # Get the internal path for storing content
        target_path = self.get_internal_path()

        # Write content to the internal path
        if not self._write_content_to_file(target_path, content, encoding):
          return None

        # Update file properties to reflect it's now a local file
        self.path = target_path
        self.is_reference = False
        self.status = FileStatus.ACTIVE
      else:
        # For non-reference files, use existing path
        if not self._write_content_to_file(self.path, content, encoding):
          return None
    # Otherwise, if not a reference, copy external file to storage
    elif not self.is_reference and not self.copy_to_storage():
      logger.error(f"Failed to save file {self.file_id}")
      return None

    # Update the metadata dictionary via the hook
    # Subclasses override this to add their specific fields.
    try:
      self._update_metadata()
    except Exception as e:
      logger.error(f"Error during metadata update hook for {self.file_id}: {e}")
      # Optionally, decide if this error should prevent saving metadata
      # For now, we log and continue, attempting to save whatever metadata exists.

    # Save metadata *after* the hook has run
    if not self.save_metadata():
      logger.error(f"Failed to save updated metadata for file {self.file_id}")
      return None

    return self.path

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
    if it exists. For URL references, it will download and export the content.

    Args:
      target_path: Path where the file should be exported
      force_overwrite: Whether to overwrite the file if it already exists

    Returns:
      bool: True if the file was exported successfully, False otherwise
    """
    # Check if target already exists
    if os.path.exists(target_path) and not force_overwrite:
      logger.error(f"Target path already exists and force_overwrite is False: {target_path}")
      return False

    # Handle URL references as a special case first
    if self.is_reference and self._is_url(self.path):
      try:
        # Download the content
        content = self._fetch_url_content(self.path)
        if content is None:
          logger.error(f"Failed to download content from URL for export: {self.path}")
          return False

        # Create target directory if it doesn't exist
        target_dir = os.path.dirname(target_path)
        if target_dir and not os.path.exists(target_dir):
          os.makedirs(target_dir, exist_ok=True)

        # Write content to the target path
        with open(target_path, 'wb') as f:
          f.write(content)

        logger.debug(f"Exported URL reference {self.file_id} to {target_path}")
        return True
      except Exception as e:
        logger.error(f"Failed to export URL reference {self.file_id} to {target_path}: {e}")
        return False

    # For regular files and local references, check if file exists
    if not self.exists():
      logger.error(f"Cannot export non-existent file: {self.file_id}")
      return False

    try:
      # Create target directory if it doesn't exist
      target_dir = os.path.dirname(target_path)
      if target_dir and not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

      # Copy the file to the target path
      source_path = self.path
      shutil.copy2(source_path, target_path)

      logger.debug(f"Exported file {self.file_id} to {target_path}")
      return True
    except Exception as e:
      logger.error(f"Failed to export file {self.file_id} to {target_path}: {e}")
      return False

  @classmethod
  def load(cls: Type[T], file_id: str, base_directory: str, load_content: bool = False) -> Optional[Dict[str, Any]]:
    """
    Load a file from its ID.

    Args:
      file_id: The ID of the file to load
      base_directory: The base directory for file operations
      load_content: Whether to load the file contents (default: False)

    Returns:
      Optional[Dict[str, Any]]: Dictionary containing metadata and optionally content, or None if loading failed
    """
    manifest = FileManifest(base_directory)
    metadata = manifest.get_file_metadata(file_id)

    if not metadata:
      logger.error(f"File {file_id} not found in manifest")
      return None

    try:
      # Create instance with data from manifest
      file_obj = cls(
        base_directory=base_directory,
        file_name=metadata.get("file_name"),
        source_path=metadata.get("source_path"),
        is_reference=metadata.get("is_reference", False),
        file_id=file_id,
        mime_type=metadata.get("mime_type"),
        timestamp=metadata.get("timestamp"),
        metadata=metadata.get("metadata", {})
      )

      # Prepare result dictionary
      result = {
        "metadata": metadata
      }

      # Load content if requested
      if load_content:
        content = file_obj._load_content()
        if content is not None:
          result["content"] = content

      return result
    except Exception as e:
      logger.error(f"Failed to load file {file_id}: {e}")
      return None

  def _load_content(self) -> Optional[Union[str, bytes]]:
    """
    Load the contents of the file based on its MIME type.

    This method determines how to load the file content based on the MIME type:
    - For text-based MIME types (text/*, application/json, etc.), returns string
    - For binary MIME types, returns bytes

    Returns:
      Optional[Union[str, bytes]]: The file contents as string or bytes, or None if loading failed
    """
    if not self.exists():
      logger.error(f"Cannot load content: File does not exist - {self.path}")
      return None

    try:
      # Check if this is a text-based MIME type using FileMimeType
      is_text = (
        self.mime_type.startswith('text/') or
        self.mime_type in FileMimeType.get_all_text_mime_types()
      )

      # Load content based on MIME type
      if is_text:
        # For text files, try to detect encoding from metadata or default to utf-8
        encoding = self.metadata.get('encoding', 'utf-8')
        with open(self.path, 'r', encoding=encoding) as f:
          return f.read()
      else:
        # For binary files, read as bytes
        with open(self.path, 'rb') as f:
          return f.read()
    except Exception as e:
      logger.error(f"Failed to load content from {self.path}: {e}")
      return None

  @classmethod
  def _fetch_url_content(cls, url: str, timeout: int = 30) -> Optional[bytes]:
    """
    Fetch content from a URL.

    Args:
      url: URL to fetch content from
      timeout: Request timeout in seconds

    Returns:
      Optional[bytes]: Content as bytes if successful, None otherwise
    """
    try:
      import requests
      response = requests.get(url, timeout=timeout)
      response.raise_for_status()  # Raise exception for HTTP errors
      return response.content
    except ImportError:
      logger.error("Requests library is required to download from URLs")
      return None
    except Exception as e:
      logger.error(f"Failed to download content from URL {url}: {e}")
      return None

  @staticmethod
  def _is_url(source: str) -> bool:
    """
    Check if a source string is a URL.

    Args:
      source: Source string to check

    Returns:
      bool: True if the source appears to be a URL
    """
    return source.startswith(('http://', 'https://', 'ftp://'))

  @staticmethod
  def _determine_reference_mode(source: str, is_reference: Optional[bool]) -> bool:
    """
    Determine whether a source should be treated as a reference.

    If is_reference is specified, uses that value.
    Otherwise, URLs are treated as references by default.

    Args:
      source: Source path or URL
      is_reference: Explicitly specified reference mode or None

    Returns:
      bool: The determined reference mode
    """
    # TODO: Add checks for file size, etc.

    if is_reference is not None:
      return is_reference

    # Default behavior: URLs are references unless specified otherwise
    return BaseFile._is_url(source)

  @classmethod
  def from_source(cls: Type[T],
                 source: str,
                 base_directory: str,
                 is_reference: Optional[bool] = None,
                 file_name: Optional[str] = None,
                 **kwargs) -> Optional[T]:
    """
    Create a file object from a source path (local file or URL).

    This is a unified method that handles both local files and URLs
    by intelligently determining the appropriate behavior.

    Args:
      source: Path to the source (local file path or URL)
      base_directory: Base directory for file operations
      is_reference: Whether to store only a reference (if None, auto-determined)
      file_name: Optional custom name for the file
      **kwargs: Additional arguments to pass to the constructor

    Returns:
      Optional[T]: The created file object, or None if creation failed
    """
    try:
      # Detect if the source is a URL
      is_url = cls._is_url(source)

      # Auto-determine if this is a reference based on source type
      is_reference = cls._determine_reference_mode(source, is_reference)

      # If non-reference and local file, check if it exists
      if not is_reference and not is_url and not os.path.exists(source):
        logger.error(f"File {source} does not exist")
        return None

      # If file_name is not provided, use basename of source path
      if file_name is None:
        file_name = os.path.basename(source) or "file"  # Default to "file" if basename is empty

      # Create file object with appropriate parameters
      file_obj = cls(
        base_directory=base_directory,
        file_name=file_name,
        source_path=source,
        is_reference=is_reference,
        **kwargs
      )

      # For reference files, just save metadata
      if is_reference:
        if not file_obj.save_metadata():
          logger.error(f"Failed to save metadata for reference file: {source}")
          return None
        return file_obj

      # For non-reference files, we need to get the content
      content = None

      # Get content based on source type
      if is_url:
        content = cls._fetch_url_content(source)
      else:  # Local file
        try:
          with open(source, 'rb') as f:
            content = f.read()
        except Exception as e:
          logger.error(f"Failed to read content from {source}: {e}")
          return None

      # Save the content to storage
      if content is not None:
        if file_obj.save(content=content) is None:
          logger.error(f"Failed to save content from {source}")
          return None
      else:
        # This should only happen if there was an error retrieving content
        logger.error(f"No content retrieved from {source}")
        return None

      return file_obj
    except Exception as e:
      logger.error(f"Failed to create file from source {source}: {e}")
      return None

  @classmethod
  def from_content(cls: Type[T], content: Union[str, bytes], base_directory: str,
                  file_name: str, encoding: str = "utf-8", **kwargs) -> Optional[T]:
    """
    Create a file from raw content (string or bytes).

    This is a generic implementation that derived classes can use or override.
    It handles the common steps of creating a file from in-memory content:
    1. Creating an instance of the file
    2. Ensuring the directory exists
    3. Writing content to the file
    4. Saving metadata

    Args:
      content: The raw content (string or bytes) to write to the file
      base_directory: Base directory for file storage
      file_name: Name of the file
      encoding: Encoding to use for string content (default: utf-8)
      **kwargs: Additional arguments to pass to the constructor

    Returns:
      Optional[T]: A new file instance, or None if creation failed
    """
    try:
      # Create the file instance
      file_obj = cls(
        base_directory=base_directory,
        file_name=file_name,
        **kwargs
      )

      # Save with content (which handles directory creation, writing, and metadata)
      if file_obj.save(content=content, encoding=encoding) is None:
        logger.error(f"Failed to save content to file: {file_name}")
        return None

      return file_obj
    except Exception as e:
      logger.error(f"Failed to create file from content: {e}")
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

  @classmethod
  def find_files_by_criteria(cls, base_directory: str,
                           subdirectory: Optional[str] = None,
                           metadata_filters: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    """
    Find files that match specific criteria.

    This method searches through the file manifest and returns all files that match
    the specified subdirectory and/or metadata filters.

    Args:
      base_directory: Base directory for file operations
      subdirectory: Optional subdirectory to filter by
      metadata_filters: Optional dictionary with metadata keys and values to match

    Returns:
      Dict[str, Dict[str, Any]]: Dictionary of file_id -> metadata for matching files
    """
    manifest = FileManifest(base_directory)
    all_files = manifest.get_all_files()
    matching_files = {}

    # Filter files based on criteria
    for file_id, metadata in all_files.items():
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

    return matching_files

  def convert_to_local(self) -> bool:
    """
    Converts a reference file to a local file by downloading/copying the content.

    Returns:
      bool: True if conversion was successful, False otherwise
    """
    if not self.is_reference:
      logger.debug(f"File {self.file_id} is already a non-reference file")
      return True

    # Check if the source exists
    if not self.exists():
      logger.error(f"Cannot convert reference to local: Source does not exist - {self.path}")
      return False

    # For URL references, download the content
    if self._is_url(self.path):
      try:
        content = self._fetch_url_content(self.path)
        if content is None:
          return False

        # Use the save method which now handles conversion automatically
        if self.save(content=content) is None:
          return False

        return True
      except Exception as e:
        logger.error(f"Failed to download URL content: {e}")
        return False
    else:
      # For file references, copy the file
      try:
        # Get a file handle to the source
        with open(self.path, 'rb') as source_file:
          content = source_file.read()

        # Use the save method which now handles conversion automatically
        if self.save(content=content) is None:
          return False

        return True
      except Exception as e:
        logger.error(f"Failed to copy file: {e}")
        return False

  @staticmethod
  def _url_exists(url: str, timeout: int = 5) -> bool:
    """
    Check if a URL exists by sending a HEAD request.

    Args:
      url: URL to check
      timeout: Request timeout in seconds

    Returns:
      bool: True if the URL exists (returns 2xx status code), False otherwise
    """
    try:
      import requests
      response = requests.head(url, timeout=timeout, allow_redirects=True)
      return response.status_code >= 200 and response.status_code < 300
    except Exception as e:
      logger.debug(f"Failed to check URL existence: {url} - {e}")
      return False