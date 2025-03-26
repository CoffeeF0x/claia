"""
Tests for the TextFile class.
"""

# External dependencies
import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock

# Internal dependencies
from files import TextFile



########################################################################
#                            TEXTFILE TESTS                            #
########################################################################
def test_initialization(temp_dir):
  """Test TextFile initialization."""
  # Basic initialization
  text_file = TextFile(
    base_directory=temp_dir,
    file_name="test.txt"
  )
  
  assert text_file.base_directory == temp_dir
  assert text_file.file_name == "test.txt"
  assert text_file.mime_type == "text/plain"
  
  # Specialized MIME type detection
  md_file = TextFile(
    base_directory=temp_dir,
    file_name="readme.md"
  )
  
  assert md_file.mime_type == "text/markdown"
  
  json_file = TextFile(
    base_directory=temp_dir,
    file_name="data.json"
  )
  
  assert json_file.mime_type == "application/json"
  
  # Text-specific attributes
  assert text_file.encoding == "utf-8"  # Default encoding
  assert text_file.line_count == 0
  assert text_file.word_count == 0
  assert text_file.char_count == 0
  
  # With source path
  text_file_with_path = TextFile(
    base_directory=temp_dir,
    file_name="external.txt",
    source_path=os.path.join(temp_dir, "some_file.txt"),
    is_reference=True
  )
  
  assert text_file_with_path.is_reference is True


def test_detect_encoding(temp_dir):
  """Test encoding detection."""
  # Create a file with a specific encoding
  test_file_path = os.path.join(temp_dir, "utf8_file.txt")
  with open(test_file_path, "w", encoding="utf-8") as f:
    f.write("This is UTF-8 text with special chars: àéêöüß")
  
  # Create a text file instance
  text_file = TextFile.from_source(test_file_path, temp_dir)
  text_file.save()
  
  # Test encoding detection
  with patch('chardet.detect') as mock_detect:
    mock_detect.return_value = {"encoding": "utf-8", "confidence": 0.9}
    
    encoding = text_file.detect_encoding()
    assert encoding == "utf-8"
    assert text_file.encoding == "utf-8"
  
  # Test low confidence result (should default to utf-8)
  with patch('chardet.detect') as mock_detect:
    mock_detect.return_value = {"encoding": "ISO-8859-1", "confidence": 0.5}
    
    encoding = text_file.detect_encoding()
    assert encoding == "utf-8"


def test_get_stats(temp_dir):
  """Test getting text file statistics."""
  # Create a file with some content
  test_file_path = os.path.join(temp_dir, "stats_test.txt")
  content = "Line one.\nLine two.\nLine three with more words."
  with open(test_file_path, "w") as f:
    f.write(content)
  
  # Create a text file instance
  text_file = TextFile.from_source(test_file_path, temp_dir)
  text_file.save()
  
  # Get stats
  stats = text_file.get_stats()
  
  # Verify stats
  assert stats["line_count"] == 3
  assert stats["word_count"] == 9
  assert stats["char_count"] == 47  # Including newlines
  
  # Verify the stats were saved in metadata
  assert text_file.line_count == 3
  assert text_file.word_count == 9
  assert text_file.char_count == 47
  assert text_file.metadata["line_count"] == 3
  assert text_file.metadata["word_count"] == 9
  assert text_file.metadata["char_count"] == 47


def test_get_preview(temp_dir):
  """Test getting a preview of text content."""
  # Create a file with many lines
  test_file_path = os.path.join(temp_dir, "preview_test.txt")
  with open(test_file_path, "w") as f:
    for i in range(20):
      f.write(f"Line {i+1}\n")
  
  # Create a text file instance
  text_file = TextFile.from_source(test_file_path, temp_dir)
  text_file.save()
  
  # Get preview with default max_lines (10)
  preview = text_file.get_preview()
  
  # Should include first 10 lines and ...
  assert preview.count("\n") == 10
  assert "Line 1" in preview
  assert "Line 10" in preview
  assert "..." in preview
  assert "Line 11" not in preview
  
  # Get preview with custom max_lines
  preview = text_file.get_preview(max_lines=5)
  
  # Should include only 5 lines and ...
  assert preview.count("\n") == 5
  assert "Line 1" in preview
  assert "Line 5" in preview
  assert "..." in preview
  assert "Line 6" not in preview


def test_search(temp_dir):
  """Test searching in text content."""
  # Create a file with mixed content
  test_file_path = os.path.join(temp_dir, "search_test.txt")
  with open(test_file_path, "w") as f:
    f.write("First line with apple\n")
    f.write("Second line with orange\n")
    f.write("Third line with Apple again\n")
    f.write("Fourth line with no fruit\n")
    f.write("Fifth line with APPLE uppercase\n")
  
  # Create a text file instance
  text_file = TextFile.from_source(test_file_path, temp_dir)
  text_file.save()
  
  # Case-insensitive search
  results = text_file.search("apple")
  assert len(results) == 3
  assert results[0][0] == 1  # Line 1
  assert "First line" in results[0][1]
  assert results[1][0] == 3  # Line 3
  assert "Third line" in results[1][1]
  assert results[2][0] == 5  # Line 5
  assert "Fifth line" in results[2][1]
  
  # Case-sensitive search
  results = text_file.search("Apple", case_sensitive=True)
  assert len(results) == 1
  assert results[0][0] == 3  # Line 3
  assert "Third line" in results[0][1]
  
  # Regex search
  results = text_file.search(r"\bno\s+\w+\b")  # "no" followed by a word
  assert len(results) == 1
  assert results[0][0] == 4  # Line 4
  assert "Fourth line" in results[0][1]


def test_get_content(temp_dir):
  """Test getting complete file content."""
  # Create a file with some content
  test_file_path = os.path.join(temp_dir, "content_test.txt")
  content = "Line one.\nLine two.\nLine three."
  with open(test_file_path, "w") as f:
    f.write(content)
  
  # Create a text file instance
  text_file = TextFile.from_source(test_file_path, temp_dir)
  text_file.save()
  
  # Get content
  file_content = text_file.get_content()
  
  # Verify exact content match
  assert file_content == content


def test_get_lines(temp_dir):
  """Test getting specific lines."""
  # Create a file with multiple lines
  test_file_path = os.path.join(temp_dir, "lines_test.txt")
  with open(test_file_path, "w") as f:
    for i in range(10):
      f.write(f"Line {i+1}\n")
  
  # Create a text file instance
  text_file = TextFile.from_source(test_file_path, temp_dir)
  text_file.save()
  
  # Get all lines
  all_lines = text_file.get_lines()
  assert len(all_lines) == 10
  assert all_lines[0] == "Line 1"
  assert all_lines[9] == "Line 10"
  
  # Get specific range
  middle_lines = text_file.get_lines(start=3, end=6)
  assert len(middle_lines) == 4  # Lines 3, 4, 5, 6
  assert middle_lines[0] == "Line 3"
  assert middle_lines[3] == "Line 6"
  
  # Get from specific line to end
  end_lines = text_file.get_lines(start=8)
  assert len(end_lines) == 3  # Lines 8, 9, 10
  assert end_lines[0] == "Line 8"
  assert end_lines[2] == "Line 10"
  
  # Handle out-of-bounds indices gracefully
  too_far = text_file.get_lines(start=100)
  assert len(too_far) == 0 