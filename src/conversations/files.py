"""
This module contains file handling classes for different file types in CLAIA.
"""

# External dependencies
import os
import mimetypes
import uuid
import logging
from typing import Dict, Any, Optional, BinaryIO
from abc import ABC, abstractmethod

# Internal dependencies
from conversations.base import BaseFile

# Setup logging
logger = logging.getLogger(__name__)


###########################################################################
#                              FILE CLASSES                               #
###########################################################################
class FileReference(BaseFile):
  """Base class for referencing files within conversations."""

  def __init__(self, file_path: str, file_id: Optional[str] = None, base_directory: Optional[str] = None):
    # If base_directory is provided, use it; otherwise, use the directory of the file
    base_dir = base_directory or os.path.dirname(file_path)
    super().__init__(base_dir)

    self.file_id = file_id or str(uuid.uuid4())
    self.file_path = file_path
    self.file_name = os.path.basename(file_path)
    self.mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    self.metadata = {}

    # Validate that the file exists
    if not os.path.exists(file_path):
      logger.warning(f"File {file_path} does not exist")

  def to_dict(self) -> Dict[str, Any]:
    """
    Convert the file reference to a dictionary.

    Returns:
        Dict[str, Any]: The file reference as a dictionary
    """
    return {
      "file_id": self.file_id,
      "file_path": self.file_path,
      "file_name": self.file_name,
      "mime_type": self.mime_type,
      "metadata": self.metadata
    }

  @classmethod
  def from_dict(cls, data: Dict[str, Any], base_directory: Optional[str] = None) -> 'FileReference':
    """
    Create a file reference from a dictionary.

    Args:
        data: The dictionary containing the file reference data
        base_directory: Optional base directory for file operations

    Returns:
        FileReference: The created file reference
    """
    instance = cls(
      file_path=data["file_path"],
      file_id=data["file_id"],
      base_directory=base_directory
    )
    instance.file_name = data["file_name"]
    instance.mime_type = data["mime_type"]
    instance.metadata = data.get("metadata", {})
    return instance

  def file_exists(self) -> bool:
    """
    Check if the referenced file exists.

    Returns:
        bool: True if the file exists, False otherwise
    """
    return os.path.exists(self.file_path)

  def get_file_size(self) -> int:
    """
    Get the size of the referenced file.

    Returns:
        int: The size of the file in bytes, or 0 if the file doesn't exist
    """
    try:
      return os.path.getsize(self.file_path) if self.file_exists() else 0
    except Exception as e:
      logger.error(f"Failed to get file size for {self.file_path}: {e}")
      return 0


###########################################################################
#                           FILE TYPE HANDLERS                            #
###########################################################################
class FileHandler(ABC):
  """Abstract base class for file type handlers."""

  @abstractmethod
  def process(self, file_reference: FileReference) -> Dict[str, Any]:
    """Process the file and return extracted data."""
    pass

  @abstractmethod
  def get_preview(self, file_reference: FileReference) -> str:
    """Get a text preview of the file for display in conversations."""
    pass

  @classmethod
  def get_handler_for_file(cls, file_reference: FileReference) -> 'FileHandler':
    """
    Factory method to get the appropriate handler for a file type.

    Args:
        file_reference: The file reference to get a handler for

    Returns:
        FileHandler: The appropriate handler for the file type
    """
    mime_type = file_reference.mime_type

    if mime_type.startswith("image/"):
      return ImageFileHandler()
    elif mime_type.startswith("audio/"):
      return AudioFileHandler()
    elif mime_type.startswith("text/"):
      return TextFileHandler()
    elif mime_type.startswith("model/"):
      return Model3DFileHandler()
    else:
      return GenericFileHandler()


class TextFileHandler(FileHandler):
  def process(self, file_reference: FileReference) -> Dict[str, Any]:
    """
    Process a text file and return extracted data.

    Args:
        file_reference: The file reference to process

    Returns:
        Dict[str, Any]: The extracted data
    """
    try:
      if not file_reference.file_exists():
        return {"error": "File does not exist"}

      with open(file_reference.file_path, 'r') as f:
        content = f.read()

      return {
        "content": content,
        "char_count": len(content),
        "line_count": content.count('\n') + 1
      }
    except Exception as e:
      logger.error(f"Failed to process text file {file_reference.file_path}: {e}")
      return {"error": str(e)}

  def get_preview(self, file_reference: FileReference) -> str:
    """
    Get a text preview of the file for display in conversations.

    Args:
        file_reference: The file reference to get a preview for

    Returns:
        str: A preview of the file content
    """
    try:
      if not file_reference.file_exists():
        return "[File not found]"

      with open(file_reference.file_path, 'r') as f:
        content = f.read(1000)  # First 1000 chars

      if len(content) == 1000:
        content += "...(truncated)"

      return content
    except Exception as e:
      logger.error(f"Failed to get preview for {file_reference.file_path}: {e}")
      return f"[Error reading file: {str(e)}]"


class ImageFileHandler(FileHandler):
  def process(self, file_reference: FileReference) -> Dict[str, Any]:
    """
    Process an image file and return extracted data.

    Args:
        file_reference: The file reference to process

    Returns:
        Dict[str, Any]: The extracted data
    """
    try:
      if not file_reference.file_exists():
        return {"error": "File does not exist"}

      # In a real implementation, you might use PIL or another library
      # to extract image dimensions, format, etc.
      return {
        "type": "image",
        "format": file_reference.file_path.split('.')[-1].lower(),
        "size_bytes": file_reference.get_file_size()
      }
    except Exception as e:
      logger.error(f"Failed to process image file {file_reference.file_path}: {e}")
      return {"error": str(e)}

  def get_preview(self, file_reference: FileReference) -> str:
    """
    Get a text preview of the image for display in conversations.

    Args:
        file_reference: The file reference to get a preview for

    Returns:
        str: A preview of the image
    """
    if not file_reference.file_exists():
      return "[Image not found]"

    return f"[Image: {file_reference.file_name}]"


class AudioFileHandler(FileHandler):
  def process(self, file_reference: FileReference) -> Dict[str, Any]:
    """
    Process an audio file and return extracted data.

    Args:
        file_reference: The file reference to process

    Returns:
        Dict[str, Any]: The extracted data
    """
    try:
      if not file_reference.file_exists():
        return {"error": "File does not exist"}

      # In a real implementation, you might use a library like pydub
      # to extract audio duration, format, etc.
      return {
        "type": "audio",
        "format": file_reference.file_path.split('.')[-1].lower(),
        "size_bytes": file_reference.get_file_size()
      }
    except Exception as e:
      logger.error(f"Failed to process audio file {file_reference.file_path}: {e}")
      return {"error": str(e)}

  def get_preview(self, file_reference: FileReference) -> str:
    """
    Get a text preview of the audio for display in conversations.

    Args:
        file_reference: The file reference to get a preview for

    Returns:
        str: A preview of the audio
    """
    if not file_reference.file_exists():
      return "[Audio not found]"

    return f"[Audio: {file_reference.file_name}]"


class Model3DFileHandler(FileHandler):
  def process(self, file_reference: FileReference) -> Dict[str, Any]:
    """
    Process a 3D model file and return extracted data.

    Args:
        file_reference: The file reference to process

    Returns:
        Dict[str, Any]: The extracted data
    """
    try:
      if not file_reference.file_exists():
        return {"error": "File does not exist"}

      return {
        "type": "3d_model",
        "format": file_reference.file_path.split('.')[-1].lower(),
        "size_bytes": file_reference.get_file_size()
      }
    except Exception as e:
      logger.error(f"Failed to process 3D model file {file_reference.file_path}: {e}")
      return {"error": str(e)}

  def get_preview(self, file_reference: FileReference) -> str:
    """
    Get a text preview of the 3D model for display in conversations.

    Args:
        file_reference: The file reference to get a preview for

    Returns:
        str: A preview of the 3D model
    """
    if not file_reference.file_exists():
      return "[3D Model not found]"

    return f"[3D Model: {file_reference.file_name}]"


class GenericFileHandler(FileHandler):
  def process(self, file_reference: FileReference) -> Dict[str, Any]:
    """
    Process a generic file and return extracted data.

    Args:
        file_reference: The file reference to process

    Returns:
        Dict[str, Any]: The extracted data
    """
    try:
      if not file_reference.file_exists():
        return {"error": "File does not exist"}

      return {
        "type": "generic",
        "size_bytes": file_reference.get_file_size()
      }
    except Exception as e:
      logger.error(f"Failed to process file {file_reference.file_path}: {e}")
      return {"error": str(e)}

  def get_preview(self, file_reference: FileReference) -> str:
    """
    Get a text preview of the file for display in conversations.

    Args:
        file_reference: The file reference to get a preview for

    Returns:
        str: A preview of the file
    """
    if not file_reference.file_exists():
      return "[File not found]"

    return f"[File: {file_reference.file_name}]"