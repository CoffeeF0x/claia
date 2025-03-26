"""
This module contains the text file handling class for CLAIA.
"""

# External dependencies
import os
import logging
import re
from typing import Dict, Any, Optional, Type, TypeVar, List, Tuple
import chardet

# Internal dependencies
from .base import BaseFile
from enums.file import FileMimeType



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)

# Type variable for class methods
T = TypeVar('T', bound='TextFile')



########################################################################
#                              TEXTFILE                                #
########################################################################
class TextFile(BaseFile):
  """
  Class for handling text files with specialized functionality.
  
  Features:
  - Text encoding detection and conversion
  - Content statistics (line count, word count, character count)
  - Content searching and extraction
  - Content preview generation
  """
  
  def __init__(self, base_directory: str, **kwargs):
    """
    Initialize a text file with text-specific attributes.
    
    Args:
      base_directory (str): Base directory for the file
      **kwargs: Additional arguments to pass to the parent class
                (file_name, external_path, is_reference, file_id, 
                 mime_type, timestamp, metadata, encoding, etc.)
    """
    # Extract text-specific kwargs that shouldn't be passed to parent
    encoding = kwargs.pop("encoding", "utf-8") if "encoding" in kwargs else "utf-8"
    
    super().__init__(base_directory=base_directory, **kwargs)
    
    # Set MIME type based on file extension
    self.mime_type = kwargs.get("mime_type") or FileMimeType.get_mime_type(
      self.file_name, default="text/plain"
    )
    
    # Text-specific attributes
    self.encoding = encoding
    self.line_count = kwargs.get("line_count", 0)
    self.word_count = kwargs.get("word_count", 0)
    self.char_count = kwargs.get("char_count", 0)
    
    # Initialize metadata with text-specific properties
    if "metadata" not in kwargs:
      self.metadata.update({
        "encoding": self.encoding,
        "line_count": self.line_count,
        "word_count": self.word_count,
        "char_count": self.char_count
      })
  
  @classmethod
  def from_string(cls: Type[T], content: str, base_directory: str, file_name: str = None, 
                  encoding: str = "utf-8", **kwargs) -> Optional[T]:
    """
    Create a TextFile from a string content.
    
    Args:
      content (str): The text content to save to the file
      base_directory (str): Base directory for the file
      file_name (str, optional): Name of the file, generated if not provided
      encoding (str): Encoding to use when writing the content
      **kwargs: Additional arguments to pass to the constructor
      
    Returns:
      Optional[T]: A new TextFile instance, or None if creation failed
    """
    try:
      # Set mime_type to text/plain if not specified
      if 'mime_type' not in kwargs:
        kwargs['mime_type'] = "text/plain"
      
      # Create a new TextFile instance - the file_id will be auto-generated in BaseFile
      text_file = cls(
        base_directory=base_directory,
        file_name=file_name,
        encoding=encoding,  # This will be extracted in __init__
        **kwargs
      )
      
      # Save the file with the provided content
      if text_file.save(content=content, encoding=encoding) is None:
        logger.error(f"Failed to save content to file: {text_file.file_name}")
        return None
      
      return text_file
    except Exception as e:
      logger.error(f"Failed to create TextFile from string: {e}")
      return None
  
  def _post_save_hook(self):
    """
    Update text statistics after saving.
    
    This is called automatically after save() or when using save() with content.
    """
    # Only update statistics if the file exists
    if self.exists():
      self.get_stats()
  
  def detect_encoding(self, min_confidence=0.7):
    """
    Detect the encoding of the text file.
    
    Args:
      min_confidence (float): Minimum confidence threshold for encoding detection
    
    Returns:
      str: Detected encoding or default utf-8 if detection fails or confidence is low
    """
    if not self.exists():
      return self.encoding
    
    with open(self.get_internal_path(), "rb") as f:
      raw_data = f.read()
      
    result = chardet.detect(raw_data)
    
    if result["confidence"] >= min_confidence:
      self.encoding = result["encoding"]
    else:
      # Default to utf-8 if confidence is low
      self.encoding = "utf-8"
      
    # Update metadata
    self.metadata["encoding"] = self.encoding
    return self.encoding
  
  def get_stats(self):
    """
    Get statistics about the text file (line count, word count, character count).
    
    Returns:
      dict: Dictionary of text file statistics
    """
    if not self.exists():
      return {
        "line_count": 0,
        "word_count": 0,
        "char_count": 0
      }
    
    content = self.get_content()
    
    # Calculate statistics
    lines = content.splitlines()
    self.line_count = len(lines)
    
    self.word_count = sum(len(line.split()) for line in lines)
    self.char_count = len(content)
    
    # Update metadata
    stats = {
      "line_count": self.line_count,
      "word_count": self.word_count,
      "char_count": self.char_count
    }
    self.metadata.update(stats)
    
    return stats
  
  def get_preview(self, max_lines=10):
    """
    Get a preview of the text file content.
    
    Args:
      max_lines (int): Maximum number of lines to include in the preview
    
    Returns:
      str: Preview of the text file content
    """
    if not self.exists():
      return ""
      
    lines = self.get_lines()
    
    if len(lines) <= max_lines:
      return "\n".join(lines)
    
    # Include first max_lines lines and add an indicator
    preview_lines = lines[:max_lines]
    return "\n".join(preview_lines) + "\n..."
  
  def search(self, pattern, case_sensitive=False):
    """
    Search for a pattern in the text file.
    
    Args:
      pattern (str): Pattern to search for (can be a regex pattern)
      case_sensitive (bool): Whether the search should be case-sensitive
    
    Returns:
      list: List of tuples with (line_number, line_content) for matches
    """
    if not self.exists():
      return []
    
    lines = self.get_lines()
    results = []
    
    flags = 0 if case_sensitive else re.IGNORECASE
    regex = re.compile(pattern, flags)
    
    for i, line in enumerate(lines, 1):  # 1-based line numbering
      if regex.search(line):
        results.append((i, line))
    
    return results
  
  def get_content(self):
    """
    Get the complete content of the text file.
    
    Returns:
      str: Content of the text file
    """
    if not self.exists():
      return ""
      
    try:
      with open(self.get_internal_path(), 'r', encoding=self.encoding) as f:
        return f.read()
    except UnicodeDecodeError:
      # Try to detect encoding and read again
      self.detect_encoding()
      with open(self.get_internal_path(), 'r', encoding=self.encoding) as f:
        return f.read()
  
  def get_lines(self, start=None, end=None):
    """
    Get specific lines from the text file.
    
    Args:
      start (int): Starting line index (1-based), None for first line
      end (int): Ending line index (1-based, inclusive), None for last line
    
    Returns:
      list: List of lines from the text file
    """
    if not self.exists():
      return []
      
    content = self.get_content()
    lines = content.splitlines()
    
    # Convert to 0-based indices for list slicing
    start_idx = (start - 1) if start is not None else 0
    end_idx = end if end is not None else len(lines)
    
    # Handle out-of-bounds indices
    if start_idx < 0:
      start_idx = 0
    if end_idx > len(lines):
      end_idx = len(lines)
    if start_idx >= len(lines) or start_idx >= end_idx:
      return []
    
    return lines[start_idx:end_idx] 