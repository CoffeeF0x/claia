"""
This module defines enums related to file operations in CLAIA.
"""

# External dependencies
from enum import Enum, auto
from typing import Dict
import os



########################################################################
#                         FILE SUBDIRECTORIES                          #
########################################################################
class FileSubdirectory(Enum):
  """Enum for file subdirectories used in file storage."""
  TEXT = "text"
  IMAGE = "images"
  AUDIO = "audio"
  VIDEO = "video"
  DOCUMENT = "documents"
  # SPREADSHEET = "spreadsheets"
  # PRESENTATION = "presentations"
  ARCHIVE = "archives"
  PROMPT = "prompts"
  CONVERSATION = "conversations"
  MISC = "misc"

  @classmethod
  def from_mime_type(cls, mime_type: str) -> 'FileSubdirectory':
    """Get the appropriate subdirectory based on MIME type."""
    # Use the FileMimeType categories to determine the file type
    if mime_type in FileMimeType.get_all_text_mime_types():
      return cls.TEXT
    elif mime_type in FileMimeType.get_all_image_mime_types():
      return cls.IMAGE
    elif mime_type in FileMimeType.get_all_document_mime_types():
      return cls.DOCUMENT
    elif mime_type in FileMimeType.get_all_audio_mime_types():
      return cls.AUDIO
    elif mime_type in FileMimeType.get_all_video_mime_types():
      return cls.VIDEO
    # elif mime_type in ["application/vnd.ms-excel",
    #          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
    #   return cls.SPREADSHEET
    # elif mime_type in ["application/vnd.ms-powerpoint",
    #          "application/vnd.openxmlformats-officedocument.presentationml.presentation"]:
    #   return cls.PRESENTATION
    elif mime_type in ["application/zip", "application/x-rar-compressed",
             "application/x-tar", "application/gzip"]:
      return cls.ARCHIVE
    else:
      return cls.MISC



########################################################################
#                             FILE STATUS                              #
########################################################################
class FileStatus(Enum):
  """Enum for tracking file status in the system."""
  ACTIVE = auto()    # File is active and in use
  DELETED = auto()     # File is marked for deletion
  TEMPORARY = auto()   # Temporary file that can be cleaned up
  EXTERNAL = auto()    # External file (reference only)



########################################################################
#                           FILE MIME TYPES                            #
########################################################################
class FileMimeType:
  """
  Class for mapping file extensions to MIME types.
  This centralizes all MIME type mappings in one place for consistency.
  """

  # Text file extensions
  TEXT_EXTENSIONS: Dict[str, str] = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
    ".json": "application/json",
    ".xml": "application/xml",
    ".html": "text/html",
    ".css": "text/css",
    ".js": "application/javascript",
  }

  # Image file extensions
  IMAGE_EXTENSIONS: Dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
  }

  # Document file extensions
  DOCUMENT_EXTENSIONS: Dict[str, str] = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".rtf": "application/rtf",
    ".odt": "application/vnd.oasis.opendocument.text",
  }

  # Audio file extensions
  AUDIO_EXTENSIONS: Dict[str, str] = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".aac": "audio/aac",
    ".m4a": "audio/mp4",
    ".wma": "audio/x-ms-wma",
    ".opus": "audio/opus",
  }

  # Video file extensions
  VIDEO_EXTENSIONS: Dict[str, str] = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mkv": "video/x-matroska",
    ".avi": "video/x-msvideo",
    ".mov": "video/quicktime",
    ".wmv": "video/x-ms-wmv",
    ".flv": "video/x-flv",
    ".3gp": "video/3gpp",
    ".mpeg": "video/mpeg",
    ".mpg": "video/mpeg",
  }

  # Combine all extension mappings
  ALL_EXTENSIONS = {
    **TEXT_EXTENSIONS,
    **IMAGE_EXTENSIONS,
    **DOCUMENT_EXTENSIONS,
    **AUDIO_EXTENSIONS,
    **VIDEO_EXTENSIONS,
  }

  @classmethod
  def get_mime_type(cls, file_name: str, default: str = "application/octet-stream") -> str:
    """
    Get the MIME type for a file based on its extension.

    Args:
      file_name: The name of the file
      default: The default MIME type to return if extension not found

    Returns:
      The MIME type for the file
    """
    if not file_name:
      return default

    _, ext = os.path.splitext(file_name.lower())
    return cls.ALL_EXTENSIONS.get(ext, default)

  @classmethod
  def get_all_text_mime_types(cls) -> set:
    """Get all text MIME types."""
    return set(cls.TEXT_EXTENSIONS.values())

  @classmethod
  def get_all_image_mime_types(cls) -> set:
    """Get all image MIME types."""
    return set(cls.IMAGE_EXTENSIONS.values())

  @classmethod
  def get_all_document_mime_types(cls) -> set:
    """Get all document MIME types."""
    return set(cls.DOCUMENT_EXTENSIONS.values())

  @classmethod
  def get_all_audio_mime_types(cls) -> set:
    """Get all audio MIME types."""
    return set(cls.AUDIO_EXTENSIONS.values())

  @classmethod
  def get_all_video_mime_types(cls) -> set:
    """Get all video MIME types."""
    return set(cls.VIDEO_EXTENSIONS.values())
