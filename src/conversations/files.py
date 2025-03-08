"""
This module contains file handling classes for different file types in CLAIA.
"""

# External dependencies
import os
import mimetypes
import uuid
from typing import Dict, Any, Optional, BinaryIO
from abc import ABC, abstractmethod

# Internal dependencies
from conversations.base import BaseFile



##################################################
#                 FILE CLASSES                   #
##################################################
class FileReference:
  """Base class for referencing files within conversations."""

  def __init__(self, file_path: str, file_id: Optional[str] = None):
    self.file_id = file_id or str(uuid.uuid4())
    self.file_path = file_path
    self.file_name = os.path.basename(file_path)
    self.mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    self.metadata = {}

  def to_dict(self) -> Dict[str, Any]:
    return {
      "file_id": self.file_id,
      "file_path": self.file_path,
      "file_name": self.file_name,
      "mime_type": self.mime_type,
      "metadata": self.metadata
    }

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> 'FileReference':
    instance = cls(file_path=data["file_path"], file_id=data["file_id"])
    instance.file_name = data["file_name"]
    instance.mime_type = data["mime_type"]
    instance.metadata = data.get("metadata", {})
    return instance



##################################################
#              FILE TYPE HANDLERS                #
##################################################
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
    """Factory method to get the appropriate handler for a file type."""
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
    with open(file_reference.file_path, 'r') as f:
      content = f.read()

    return {
      "content": content,
      "char_count": len(content),
      "line_count": content.count('\n') + 1
    }

  def get_preview(self, file_reference: FileReference) -> str:
    with open(file_reference.file_path, 'r') as f:
      content = f.read(1000)  # First 1000 chars

    if len(content) == 1000:
      content += "...(truncated)"

    return content


class ImageFileHandler(FileHandler):
  def process(self, file_reference: FileReference) -> Dict[str, Any]:
    # In a real implementation, you might use PIL or another library
    # to extract image dimensions, format, etc.
    return {
      "type": "image",
      "format": file_reference.file_path.split('.')[-1].lower()
    }

  def get_preview(self, file_reference: FileReference) -> str:
    return f"[Image: {file_reference.file_name}]"


class AudioFileHandler(FileHandler):
  def process(self, file_reference: FileReference) -> Dict[str, Any]:
    # In a real implementation, you might use a library like pydub
    # to extract audio duration, format, etc.
    return {
      "type": "audio",
      "format": file_reference.file_path.split('.')[-1].lower()
    }

  def get_preview(self, file_reference: FileReference) -> str:
    return f"[Audio: {file_reference.file_name}]"


class Model3DFileHandler(FileHandler):
  def process(self, file_reference: FileReference) -> Dict[str, Any]:
    return {
      "type": "3d_model",
      "format": file_reference.file_path.split('.')[-1].lower()
    }

  def get_preview(self, file_reference: FileReference) -> str:
    return f"[3D Model: {file_reference.file_name}]"


class GenericFileHandler(FileHandler):
  def process(self, file_reference: FileReference) -> Dict[str, Any]:
    return {
      "type": "generic",
      "size_bytes": os.path.getsize(file_reference.file_path)
    }

  def get_preview(self, file_reference: FileReference) -> str:
    return f"[File: {file_reference.file_name}]"