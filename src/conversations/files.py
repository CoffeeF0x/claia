"""
This module contains file handling classes for different file types in CLAIA.
"""

# External dependencies
import os
import base64
import mimetypes
import uuid
import logging
from typing import Dict, Any, Optional, List, BinaryIO, Type, TypeVar
from abc import ABC, abstractmethod

# Internal dependencies
from .base import BaseFile



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)

# Type variable for class methods that return the class instance
T = TypeVar('T', bound='BaseFile')



########################################################################
#                             FILE CLASSES                             #
########################################################################
class TextFile(BaseFile):
  """Class for handling text files."""

  def __init__(self, file_path: str, base_directory: str, **kwargs):
    """
    Initialize a TextFile object.

    Args:
        file_path: The path to the file
        base_directory: The base directory for file operations
        **kwargs: Additional arguments to pass to the BaseFile constructor
    """
    super().__init__(file_path, base_directory, **kwargs)
    self.content = None
    self.line_count = 0
    self.char_count = 0

  def process(self) -> Dict[str, Any]:
    """
    Process the text file and extract its content and metadata.

    Returns:
        Dict[str, Any]: The extracted data
    """
    try:
      if not self.file_exists():
        return {"error": "File does not exist"}

      with open(self.file_path, 'r', encoding='utf-8') as f:
        self.content = f.read()

      self.char_count = len(self.content)
      self.line_count = self.content.count('\n') + 1

      self.metadata.update({
        "char_count": self.char_count,
        "line_count": self.line_count
      })

      return {
        "content": self.content,
        "char_count": self.char_count,
        "line_count": self.line_count
      }
    except Exception as e:
      logger.error(f"Failed to process text file {self.file_path}: {e}")
      return {"error": str(e)}

  def get_preview(self, max_length: int = 1000) -> str:
    """
    Get a preview of the text file.

    Args:
        max_length: The maximum length of the preview

    Returns:
        str: A preview of the file content
    """
    try:
      if self.content is None:
        self.process()

      if self.content is None:
        return "[File not found or could not be processed]"

      if len(self.content) > max_length:
        return self.content[:max_length] + "...(truncated)"

      return self.content
    except Exception as e:
      logger.error(f"Failed to get preview for {self.file_path}: {e}")
      return f"[Error reading file: {str(e)}]"

  @classmethod
  def from_dict(cls: Type[T], data: Dict[str, Any], base_directory: str) -> T:
    """
    Create a TextFile from a dictionary.

    Args:
        data: The dictionary containing the file data
        base_directory: The base directory for file operations

    Returns:
        T: The created TextFile
    """
    instance = super(TextFile, cls).from_dict(data, base_directory)
    instance.content = data.get("content")
    instance.char_count = data.get("char_count", 0)
    instance.line_count = data.get("line_count", 0)
    return instance

  def to_dict(self) -> Dict[str, Any]:
    """
    Convert the TextFile to a dictionary.

    Returns:
        Dict[str, Any]: The TextFile as a dictionary
    """
    data = super().to_dict()
    data.update({
      "content": self.content,
      "char_count": self.char_count,
      "line_count": self.line_count
    })
    return data


class ImageFile(BaseFile):
  """Class for handling image files."""

  def __init__(self, file_path: str, base_directory: str, **kwargs):
    """
    Initialize an ImageFile object.

    Args:
        file_path: The path to the file
        base_directory: The base directory for file operations
        **kwargs: Additional arguments to pass to the BaseFile constructor
    """
    super().__init__(file_path, base_directory, **kwargs)
    self.width = 0
    self.height = 0
    self.format = os.path.splitext(file_path)[1].lstrip('.').lower()

  def process(self) -> Dict[str, Any]:
    """
    Process the image file and extract its metadata.

    Returns:
        Dict[str, Any]: The extracted data
    """
    try:
      if not self.file_exists():
        return {"error": "File does not exist"}

      # Try to get image dimensions using PIL if available
      try:
        from PIL import Image
        with Image.open(self.file_path) as img:
          self.width, self.height = img.size
          self.format = img.format.lower()
      except ImportError:
        logger.warning("PIL not available, cannot extract image dimensions")

      self.metadata.update({
        "width": self.width,
        "height": self.height,
        "format": self.format,
        "size_bytes": self.get_file_size()
      })

      return {
        "width": self.width,
        "height": self.height,
        "format": self.format,
        "size_bytes": self.get_file_size()
      }
    except Exception as e:
      logger.error(f"Failed to process image file {self.file_path}: {e}")
      return {"error": str(e)}

  def get_preview(self) -> str:
    """
    Get a preview of the image file.

    Returns:
        str: A preview of the image
    """
    if not self.file_exists():
      return "[Image not found]"

    dimensions = f"{self.width}x{self.height}" if self.width and self.height else "unknown dimensions"
    return f"[Image: {self.file_name}, {dimensions}, {self.format}]"

  def get_base64(self) -> Optional[str]:
    """
    Get the image as a base64-encoded string.

    Returns:
        Optional[str]: The base64-encoded image, or None if encoding failed
    """
    try:
      if not self.file_exists():
        return None

      with open(self.file_path, 'rb') as f:
        image_data = f.read()

      return base64.b64encode(image_data).decode('utf-8')
    except Exception as e:
      logger.error(f"Failed to encode image {self.file_path} as base64: {e}")
      return None

  @classmethod
  def from_dict(cls: Type[T], data: Dict[str, Any], base_directory: str) -> T:
    """
    Create an ImageFile from a dictionary.

    Args:
        data: The dictionary containing the file data
        base_directory: The base directory for file operations

    Returns:
        T: The created ImageFile
    """
    instance = super(ImageFile, cls).from_dict(data, base_directory)
    instance.width = data.get("width", 0)
    instance.height = data.get("height", 0)
    instance.format = data.get("format", "")
    return instance

  def to_dict(self) -> Dict[str, Any]:
    """
    Convert the ImageFile to a dictionary.

    Returns:
        Dict[str, Any]: The ImageFile as a dictionary
    """
    data = super().to_dict()
    data.update({
      "width": self.width,
      "height": self.height,
      "format": self.format
    })
    return data


class AudioFile(BaseFile):
  """Class for handling audio files."""

  def __init__(self, file_path: str, base_directory: str, **kwargs):
    """
    Initialize an AudioFile object.

    Args:
        file_path: The path to the file
        base_directory: The base directory for file operations
        **kwargs: Additional arguments to pass to the BaseFile constructor
    """
    super().__init__(file_path, base_directory, **kwargs)
    self.duration = 0
    self.format = os.path.splitext(file_path)[1].lstrip('.').lower()
    self.sample_rate = 0
    self.channels = 0

  def process(self) -> Dict[str, Any]:
    """
    Process the audio file and extract its metadata.

    Returns:
        Dict[str, Any]: The extracted data
    """
    try:
      if not self.file_exists():
        return {"error": "File does not exist"}

      # Try to get audio metadata using pydub if available
      try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(self.file_path)
        self.duration = len(audio) / 1000.0  # Convert ms to seconds
        self.sample_rate = audio.frame_rate
        self.channels = audio.channels
      except ImportError:
        logger.warning("pydub not available, cannot extract audio metadata")

      self.metadata.update({
        "duration": self.duration,
        "format": self.format,
        "sample_rate": self.sample_rate,
        "channels": self.channels,
        "size_bytes": self.get_file_size()
      })

      return {
        "duration": self.duration,
        "format": self.format,
        "sample_rate": self.sample_rate,
        "channels": self.channels,
        "size_bytes": self.get_file_size()
      }
    except Exception as e:
      logger.error(f"Failed to process audio file {self.file_path}: {e}")
      return {"error": str(e)}

  def get_preview(self) -> str:
    """
    Get a preview of the audio file.

    Returns:
        str: A preview of the audio
    """
    if not self.file_exists():
      return "[Audio not found]"

    duration_str = f"{self.duration:.2f} seconds" if self.duration else "unknown duration"
    return f"[Audio: {self.file_name}, {duration_str}, {self.format}]"

  @classmethod
  def from_dict(cls: Type[T], data: Dict[str, Any], base_directory: str) -> T:
    """
    Create an AudioFile from a dictionary.

    Args:
        data: The dictionary containing the file data
        base_directory: The base directory for file operations

    Returns:
        T: The created AudioFile
    """
    instance = super(AudioFile, cls).from_dict(data, base_directory)
    instance.duration = data.get("duration", 0)
    instance.format = data.get("format", "")
    instance.sample_rate = data.get("sample_rate", 0)
    instance.channels = data.get("channels", 0)
    return instance

  def to_dict(self) -> Dict[str, Any]:
    """
    Convert the AudioFile to a dictionary.

    Returns:
        Dict[str, Any]: The AudioFile as a dictionary
    """
    data = super().to_dict()
    data.update({
      "duration": self.duration,
      "format": self.format,
      "sample_rate": self.sample_rate,
      "channels": self.channels
    })
    return data


class VideoFile(BaseFile):
  """Class for handling video files."""

  def __init__(self, file_path: str, base_directory: str, **kwargs):
    """
    Initialize a VideoFile object.

    Args:
        file_path: The path to the file
        base_directory: The base directory for file operations
        **kwargs: Additional arguments to pass to the BaseFile constructor
    """
    super().__init__(file_path, base_directory, **kwargs)
    self.duration = 0
    self.width = 0
    self.height = 0
    self.format = os.path.splitext(file_path)[1].lstrip('.').lower()
    self.fps = 0

  def process(self) -> Dict[str, Any]:
    """
    Process the video file and extract its metadata.

    Returns:
        Dict[str, Any]: The extracted data
    """
    try:
      if not self.file_exists():
        return {"error": "File does not exist"}

      # Try to get video metadata using moviepy if available
      try:
        from moviepy.editor import VideoFileClip
        clip = VideoFileClip(self.file_path)
        self.duration = clip.duration
        self.width, self.height = clip.size
        self.fps = clip.fps
        clip.close()
      except ImportError:
        logger.warning("moviepy not available, cannot extract video metadata")

      self.metadata.update({
        "duration": self.duration,
        "width": self.width,
        "height": self.height,
        "format": self.format,
        "fps": self.fps,
        "size_bytes": self.get_file_size()
      })

      return {
        "duration": self.duration,
        "width": self.width,
        "height": self.height,
        "format": self.format,
        "fps": self.fps,
        "size_bytes": self.get_file_size()
      }
    except Exception as e:
      logger.error(f"Failed to process video file {self.file_path}: {e}")
      return {"error": str(e)}

  def get_preview(self) -> str:
    """
    Get a preview of the video file.

    Returns:
        str: A preview of the video
    """
    if not self.file_exists():
      return "[Video not found]"

    duration_str = f"{self.duration:.2f} seconds" if self.duration else "unknown duration"
    dimensions = f"{self.width}x{self.height}" if self.width and self.height else "unknown dimensions"
    return f"[Video: {self.file_name}, {duration_str}, {dimensions}, {self.format}]"

  @classmethod
  def from_dict(cls: Type[T], data: Dict[str, Any], base_directory: str) -> T:
    """
    Create a VideoFile from a dictionary.

    Args:
        data: The dictionary containing the file data
        base_directory: The base directory for file operations

    Returns:
        T: The created VideoFile
    """
    instance = super(VideoFile, cls).from_dict(data, base_directory)
    instance.duration = data.get("duration", 0)
    instance.width = data.get("width", 0)
    instance.height = data.get("height", 0)
    instance.format = data.get("format", "")
    instance.fps = data.get("fps", 0)
    return instance

  def to_dict(self) -> Dict[str, Any]:
    """
    Convert the VideoFile to a dictionary.

    Returns:
        Dict[str, Any]: The VideoFile as a dictionary
    """
    data = super().to_dict()
    data.update({
      "duration": self.duration,
      "width": self.width,
      "height": self.height,
      "format": self.format,
      "fps": self.fps
    })
    return data


class DocumentFile(BaseFile):
  """Class for handling document files (PDF, Word, etc.)."""

  def __init__(self, file_path: str, base_directory: str, **kwargs):
    """
    Initialize a DocumentFile object.

    Args:
        file_path: The path to the file
        base_directory: The base directory for file operations
        **kwargs: Additional arguments to pass to the BaseFile constructor
    """
    super().__init__(file_path, base_directory, **kwargs)
    self.page_count = 0
    self.format = os.path.splitext(file_path)[1].lstrip('.').lower()
    self.text_content = None

  def process(self) -> Dict[str, Any]:
    """
    Process the document file and extract its metadata.

    Returns:
        Dict[str, Any]: The extracted data
    """
    try:
      if not self.file_exists():
        return {"error": "File does not exist"}

      # Try to extract text from PDF if available
      if self.format == "pdf":
        try:
          import PyPDF2
          with open(self.file_path, 'rb') as f:
            pdf = PyPDF2.PdfReader(f)
            self.page_count = len(pdf.pages)

            # Extract text from first few pages
            text = []
            for i in range(min(5, self.page_count)):
              text.append(pdf.pages[i].extract_text())
            self.text_content = "\n".join(text)
        except ImportError:
          logger.warning("PyPDF2 not available, cannot extract PDF metadata")

      self.metadata.update({
        "page_count": self.page_count,
        "format": self.format,
        "size_bytes": self.get_file_size()
      })

      return {
        "page_count": self.page_count,
        "format": self.format,
        "text_content": self.text_content,
        "size_bytes": self.get_file_size()
      }
    except Exception as e:
      logger.error(f"Failed to process document file {self.file_path}: {e}")
      return {"error": str(e)}

  def get_preview(self) -> str:
    """
    Get a preview of the document file.

    Returns:
        str: A preview of the document
    """
    if not self.file_exists():
      return "[Document not found]"

    pages_str = f"{self.page_count} pages" if self.page_count else "unknown page count"

    if self.text_content:
      preview = self.text_content[:500] + "..." if len(self.text_content) > 500 else self.text_content
      return f"[Document: {self.file_name}, {pages_str}, {self.format}]\n\nPreview:\n{preview}"

    return f"[Document: {self.file_name}, {pages_str}, {self.format}]"

  @classmethod
  def from_dict(cls: Type[T], data: Dict[str, Any], base_directory: str) -> T:
    """
    Create a DocumentFile from a dictionary.

    Args:
        data: The dictionary containing the file data
        base_directory: The base directory for file operations

    Returns:
        T: The created DocumentFile
    """
    instance = super(DocumentFile, cls).from_dict(data, base_directory)
    instance.page_count = data.get("page_count", 0)
    instance.format = data.get("format", "")
    instance.text_content = data.get("text_content")
    return instance

  def to_dict(self) -> Dict[str, Any]:
    """
    Convert the DocumentFile to a dictionary.

    Returns:
        Dict[str, Any]: The DocumentFile as a dictionary
    """
    data = super().to_dict()
    data.update({
      "page_count": self.page_count,
      "format": self.format,
      "text_content": self.text_content
    })
    return data


class GenericFile(BaseFile):
  """Class for handling generic files that don't fit into other categories."""

  def __init__(self, file_path: str, base_directory: str, **kwargs):
    """
    Initialize a GenericFile object.

    Args:
        file_path: The path to the file
        base_directory: The base directory for file operations
        **kwargs: Additional arguments to pass to the BaseFile constructor
    """
    super().__init__(file_path, base_directory, **kwargs)
    self.format = os.path.splitext(file_path)[1].lstrip('.').lower()

  def process(self) -> Dict[str, Any]:
    """
    Process the generic file and extract its metadata.

    Returns:
        Dict[str, Any]: The extracted data
    """
    try:
      if not self.file_exists():
        return {"error": "File does not exist"}

      self.metadata.update({
        "format": self.format,
        "size_bytes": self.get_file_size()
      })

      return {
        "format": self.format,
        "size_bytes": self.get_file_size()
      }
    except Exception as e:
      logger.error(f"Failed to process file {self.file_path}: {e}")
      return {"error": str(e)}

  def get_preview(self) -> str:
    """
    Get a preview of the generic file.

    Returns:
        str: A preview of the file
    """
    if not self.file_exists():
      return "[File not found]"

    size_str = f"{self.get_file_size() / 1024:.2f} KB" if self.get_file_size() else "unknown size"
    return f"[File: {self.file_name}, {size_str}, {self.format}]"

  @classmethod
  def from_dict(cls: Type[T], data: Dict[str, Any], base_directory: str) -> T:
    """
    Create a GenericFile from a dictionary.

    Args:
        data: The dictionary containing the file data
        base_directory: The base directory for file operations

    Returns:
        T: The created GenericFile
    """
    instance = super(GenericFile, cls).from_dict(data, base_directory)
    instance.format = data.get("format", "")
    return instance

  def to_dict(self) -> Dict[str, Any]:
    """
    Convert the GenericFile to a dictionary.

    Returns:
        Dict[str, Any]: The GenericFile as a dictionary
    """
    data = super().to_dict()
    data.update({
      "format": self.format
    })
    return data



########################################################################
#                           FILE FACTORY                               #
########################################################################
class FileFactory:
  """Factory class for creating file objects based on MIME type."""

  @staticmethod
  def create_file(file_path: str, base_directory: str, **kwargs) -> BaseFile:
    """
    Create a file object based on the file's MIME type.

    Args:
        file_path: The path to the file
        base_directory: The base directory for file operations
        **kwargs: Additional arguments to pass to the file constructor

    Returns:
        BaseFile: The created file object
    """
    mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

    if mime_type.startswith("text/") or mime_type in ["application/json", "application/xml"]:
      return TextFile(file_path, base_directory, **kwargs)
    elif mime_type.startswith("image/"):
      return ImageFile(file_path, base_directory, **kwargs)
    elif mime_type.startswith("audio/"):
      return AudioFile(file_path, base_directory, **kwargs)
    elif mime_type.startswith("video/"):
      return VideoFile(file_path, base_directory, **kwargs)
    elif mime_type in ["application/pdf", "application/msword",
                      "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
      return DocumentFile(file_path, base_directory, **kwargs)
    else:
      return GenericFile(file_path, base_directory, **kwargs)

  @staticmethod
  def load_file(file_id: str, base_directory: str) -> Optional[BaseFile]:
    """
    Load a file from its ID.

    Args:
        file_id: The ID of the file to load
        base_directory: The base directory for file operations

    Returns:
        Optional[BaseFile]: The loaded file, or None if loading failed
    """
    # First, try to load the file metadata
    file = BaseFile.load(file_id, base_directory)
    if not file:
      return None

    # Then, create the appropriate file type
    return FileFactory.create_file(
      file_path=file.file_path,
      base_directory=base_directory,
      file_id=file.file_id,
      file_name=file.file_name,
      mime_type=file.mime_type,
      timestamp=file.timestamp,
      metadata=file.metadata
    )