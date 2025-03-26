"""
Tests for the BaseFile class.
"""

# External dependencies
import pytest
import os
import shutil
import tempfile
import time
import uuid
from unittest.mock import patch, MagicMock
from typing import Dict, Any

# Internal dependencies
from files import BaseFile, FileManifest
from enums import FileStatus, FileSubdirectory



########################################################################
#                             BASEFILE TESTS                           #
########################################################################
def test_initialization(temp_dir, test_file):
  """Test BaseFile initialization with various parameters."""
  # Basic initialization
  base_file = BaseFile(
    base_directory=temp_dir,
    file_name="test.txt"
  )
  
  assert base_file.base_directory == temp_dir
  assert base_file.file_name == "test.txt"
  assert base_file.external_path is None
  assert base_file.is_reference is False
  assert base_file.mime_type == "text/plain"
  assert isinstance(base_file.file_id, str)
  
  # With external path
  base_file_with_external = BaseFile(
    base_directory=temp_dir,
    file_name="external_test.png",
    external_path=test_file,
    is_reference=True
  )
  
  assert base_file_with_external.file_path == test_file
  assert base_file_with_external.is_reference is True
  assert base_file_with_external.status == FileStatus.EXTERNAL
  
  # With custom file_id
  custom_id = str(uuid.uuid4())
  base_file_with_id = BaseFile(
    base_directory=temp_dir,
    file_name="id_test.txt",
    file_id=custom_id
  )
  
  assert base_file_with_id.file_id == custom_id


def test_get_file_type_and_subdirectory(base_file):
  """Test getting the file type and subdirectory for a file."""
  assert base_file.get_file_type() == FileSubdirectory.TEXT
  assert base_file.get_subdirectory() == "text"
  
  # Test with different MIME types
  with patch.object(base_file, 'mime_type', "image/jpeg"):
    assert base_file.get_file_type() == FileSubdirectory.IMAGE
    assert base_file.get_subdirectory() == "images"
  
  with patch.object(base_file, 'mime_type', "audio/mpeg"):
    assert base_file.get_file_type() == FileSubdirectory.AUDIO
    assert base_file.get_subdirectory() == "audio"


def test_ensure_directory_exists(base_file):
  """Test ensuring directories exist."""
  # Directories should be created
  assert base_file.ensure_directory_exists() is True
  
  # Check that base directory exists
  assert os.path.exists(base_file.base_directory)
  
  # Check that subdirectory exists
  subdir_path = os.path.join(base_file.base_directory, base_file.get_subdirectory())
  assert os.path.exists(subdir_path)


def test_get_full_path(base_file):
  """Test getting the full path for a file."""
  expected_path = os.path.join(
    base_file.base_directory,
    base_file.get_subdirectory(),
    base_file.file_id
  )
  assert base_file.get_full_path() == expected_path


def test_file_exists(base_file, test_file):
  """Test checking if a file exists."""
  # Use MagicMock with side_effect to control behavior based on path
  def exists_side_effect(path):
    return path == test_file
    
  with patch('os.path.exists', side_effect=exists_side_effect):
    # Set the correct external path to make file_exists work
    base_file.file_path = "non_existent_path"
    base_file.external_path = test_file
    base_file.is_reference = True
    
    # Should return True when external_path exists
    assert base_file.file_exists() is True
    
    # Should return False when neither exists
    base_file.external_path = "non_existent_path"
    assert base_file.file_exists() is False


def test_get_file_size(base_file, test_file):
  """Test getting file size."""
  # Get size from external path (test_file)
  expected_size = os.path.getsize(test_file)
  
  # Patch os.path.exists and os.path.getsize to control behavior
  with patch('os.path.exists', lambda path: True), \
       patch('os.path.getsize', lambda path: expected_size):
    assert base_file.get_file_size() == expected_size
  
  # Test when file doesn't exist
  with patch.object(base_file, 'file_exists', return_value=False):
    assert base_file.get_file_size() == 0


def test_copy_to_storage(base_file, test_file):
  """Test copying a file to storage."""
  # Make sure the directories exist first
  base_file.ensure_directory_exists()
  
  # Create a patched version that uses the actual function implementation
  # but with mocked dependencies
  with patch('files.base.shutil.copy2') as mock_copy, \
       patch('os.path.exists', lambda path: path == test_file):
    
    # Call copy_to_storage
    result = base_file.copy_to_storage()
    
    # Should return True
    assert result is True
    
    # Should call copy2 with external path as source
    mock_copy.assert_called_once_with(test_file, base_file.get_full_path())
    
    # File path should be updated to storage path
    assert base_file.file_path == base_file.get_full_path()
  
  # Test is_reference=True (should not copy)
  with patch.object(base_file, 'is_reference', True), \
       patch('shutil.copy2') as mock_copy:
    
    result = base_file.copy_to_storage()
    assert result is True
    assert not mock_copy.called  # Should not call copy2
  
  # Test when file doesn't exist
  with patch.object(base_file, 'external_path', None), \
       patch.object(base_file, 'file_path', "nonexistent.txt"), \
       patch('os.path.exists', lambda path: False), \
       patch('shutil.copy2') as mock_copy:
    
    result = base_file.copy_to_storage()
    assert result is False
    assert not mock_copy.called  # Should not call copy2


def test_to_dict(base_file):
  """Test converting file to dictionary."""
  # Convert to dict
  file_dict = base_file.to_dict()
  
  # Check required fields
  assert file_dict["file_id"] == base_file.file_id
  assert file_dict["file_name"] == base_file.file_name
  assert file_dict["file_path"] == base_file.file_path
  assert file_dict["external_path"] == base_file.external_path
  assert file_dict["is_reference"] == base_file.is_reference
  assert file_dict["mime_type"] == base_file.mime_type
  assert file_dict["timestamp"] == base_file.timestamp
  assert file_dict["status"] == base_file.status.name
  assert file_dict["subdirectory"] == base_file.get_subdirectory()
  assert "metadata" in file_dict
  assert "references" in file_dict


def test_save_metadata(base_file):
  """Test saving metadata to manifest."""
  mock_manifest = MagicMock()
  base_file.manifest = mock_manifest
  
  base_file.save_metadata()
  
  # Verify manifest's update_file_metadata was called with correct arguments
  mock_manifest.update_file_metadata.assert_called_once_with(
    base_file.file_id, base_file.to_dict()
  )


def test_save(base_file, monkeypatch, temp_dir):
  """Test saving a file and its metadata."""
  # Set is_reference to False to test actual copying
  base_file.is_reference = False
  
  # Create mocks with correct return values for the BaseFile instance methods
  mock_ensure_dir = MagicMock(return_value=True)
  mock_copy = MagicMock(return_value=True)
  mock_save_metadata = MagicMock(return_value=True)
  
  # Patch the methods on this specific instance
  monkeypatch.setattr(base_file, 'ensure_directory_exists', mock_ensure_dir)
  monkeypatch.setattr(base_file, 'copy_to_storage', mock_copy)
  monkeypatch.setattr(base_file, 'save_metadata', mock_save_metadata)
  
  # Call save method
  result = base_file.save()
  
  # Verify all methods were called
  assert mock_ensure_dir.call_count == 1
  assert mock_copy.call_count == 1
  assert mock_save_metadata.call_count == 1
  
  # Result should be the file path
  assert result == base_file.file_path
  
  # Test when ensure_directory_exists fails
  mock_ensure_dir.reset_mock()
  mock_copy.reset_mock()
  mock_save_metadata.reset_mock()
  
  mock_ensure_dir.return_value = False
  
  result = base_file.save()
  
  assert result is None
  assert mock_ensure_dir.call_count == 1
  assert mock_copy.call_count == 0  # Should not be called when ensure_directory_exists fails
  assert mock_save_metadata.call_count == 0  # Should not be called when ensure_directory_exists fails
  
  # Test saving with content
  mock_ensure_dir.reset_mock()
  mock_copy.reset_mock()
  mock_save_metadata.reset_mock()
  
  mock_ensure_dir.return_value = True
  
  # Create a real file to test content saving
  test_content = "Test content for save method"
  file_path = os.path.join(temp_dir, "test_content.txt")
  
  # Create a new BaseFile instance for this test
  content_file = BaseFile(
    base_directory=temp_dir,
    file_name="test_content.txt"
  )
  
  # Ensure we use the real ensure_directory_exists and save_metadata methods
  monkeypatch.undo()
  
  # Save with content
  result = content_file.save(content=test_content)
  
  # Verify file was created with content
  assert result is not None
  assert os.path.exists(content_file.file_path)
  
  with open(content_file.file_path, 'r') as f:
    assert f.read() == test_content
  
  # Test binary content
  binary_content = b"Binary test content"
  binary_file = BaseFile(
    base_directory=temp_dir,
    file_name="binary_content.bin",
    mime_type="application/octet-stream"
  )
  
  result = binary_file.save(content=binary_content)
  
  assert result is not None
  assert os.path.exists(binary_file.file_path)
  
  with open(binary_file.file_path, 'rb') as f:
    assert f.read() == binary_content


def test_mark_for_deletion(base_file):
  """Test marking a file for deletion."""
  mock_manifest = MagicMock()
  base_file.manifest = mock_manifest
  
  base_file.mark_for_deletion()
  
  # Status should be updated
  assert base_file.status == FileStatus.DELETED
  
  # Manifest's mark_for_deletion should be called
  mock_manifest.mark_for_deletion.assert_called_once_with(base_file.file_id)


def test_add_and_remove_reference(base_file):
  """Test adding and removing references."""
  mock_manifest = MagicMock()
  base_file.manifest = mock_manifest
  
  # Add reference
  base_file.add_reference("ref1")
  mock_manifest.add_reference.assert_called_once_with(base_file.file_id, "ref1")
  
  # Remove reference
  base_file.remove_reference("ref1")
  mock_manifest.remove_reference.assert_called_once_with(base_file.file_id, "ref1")


def test_load(temp_dir):
  """Test loading a file from manifest."""
  # Create mock manifest
  mock_manifest = MagicMock()
  mock_metadata = {
    "file_id": "test_id",
    "file_name": "loaded.txt",
    "external_path": None,
    "is_reference": False,
    "mime_type": "text/plain",
    "timestamp": time.time(),
    "metadata": {"test": "data"}
  }
  mock_manifest.get_file_metadata.return_value = mock_metadata
  
  # Patch FileManifest constructor to return our mock
  with patch('files.base.FileManifest', return_value=mock_manifest):
    # Load file
    loaded_file = BaseFile.load("test_id", temp_dir)
    
    # Verify file was loaded with correct data
    assert loaded_file is not None
    assert loaded_file.file_id == "test_id"
    assert loaded_file.file_name == "loaded.txt"
    assert loaded_file.metadata == {"test": "data"}
    
    # Test when file not found
    mock_manifest.get_file_metadata.return_value = None
    not_found = BaseFile.load("nonexistent", temp_dir)
    assert not_found is None


def test_from_path(temp_dir, test_file):
  """Test creating a file from path."""
  # Create file from path
  file = BaseFile.from_source(test_file, temp_dir)
  
  # Verify file was created with correct data
  assert file is not None
  assert file.base_directory == temp_dir
  assert file.file_name == os.path.basename(test_file)
  assert file.external_path == test_file
  assert file.is_reference is False
  
  # Reference only
  ref_file = BaseFile.from_source(test_file, temp_dir, is_reference=True)
  assert ref_file.is_reference is True
  
  # Non-existent file
  non_file = BaseFile.from_source("nonexistent.txt", temp_dir)
  assert non_file is None


def test_from_url(temp_dir):
  """Test creating a file from URL."""
  url = "https://lloydbower.com/favicon.png"
  
  # Create file from URL
  file = BaseFile.from_source(url, temp_dir)
  
  # Verify file was created with correct data
  assert file is not None
  assert file.base_directory == temp_dir
  assert file.file_name == "favicon.png"
  assert file.external_path == url
  assert file.is_reference is True
  
  # Mock _fetch_url_content for the non-reference URL test
  mock_content = b"Mock image data"
  with patch.object(BaseFile, '_fetch_url_content', return_value=mock_content):
    # Non-reference (would trigger download)
    non_ref = BaseFile.from_source(url, temp_dir, is_reference=False)
    
    # Verify the result
    assert non_ref is not None
    assert non_ref.is_reference is False
    assert non_ref.file_name == "favicon.png"


def test_export(base_file, test_file, temp_dir):
  """Test exporting a file to an external location."""
  # Setup
  export_path = os.path.join(temp_dir, "exported_file.txt")
  
  # Mock file_exists to return True
  with patch.object(base_file, 'file_exists', return_value=True), \
       patch.object(base_file, 'file_path', test_file), \
       patch('shutil.copy2') as mock_copy:
    
    # Test successful export
    result = base_file.export(export_path)
    assert result is True
    mock_copy.assert_called_once_with(test_file, export_path)
  
  # Test exporting to existing path without force_overwrite
  with patch.object(base_file, 'file_exists', return_value=True), \
       patch('os.path.exists', lambda path: path == export_path):
    
    result = base_file.export(export_path, force_overwrite=False)
    assert result is False
    
    # With force_overwrite=True
    with patch('shutil.copy2') as mock_copy:
      result = base_file.export(export_path, force_overwrite=True)
      assert result is True
      mock_copy.assert_called_once_with(base_file.file_path, export_path)
  
  # Test when source file doesn't exist
  with patch.object(base_file, 'file_exists', return_value=False):
    result = base_file.export(export_path)
    assert result is False


def test_from_content(temp_dir):
  """Test creating a file from raw content."""
  # Test with string content
  string_content = "This is test content for BaseFile.from_content"
  string_file = BaseFile.from_content(
    content=string_content,
    base_directory=temp_dir,
    file_name="string_test.txt"
  )
  
  assert string_file is not None
  assert string_file.file_name == "string_test.txt"
  assert string_file.file_exists() is True
  
  # Verify content was written correctly
  with open(string_file.file_path, 'r') as f:
    assert f.read() == string_content
  
  # Test with binary content
  binary_content = b"Binary content for testing"
  binary_file = BaseFile.from_content(
    content=binary_content,
    base_directory=temp_dir,
    file_name="binary_test.bin",
    mime_type="application/octet-stream"
  )
  
  assert binary_file is not None
  assert binary_file.file_name == "binary_test.bin"
  assert binary_file.file_exists() is True
  
  # Verify binary content was written correctly
  with open(binary_file.file_path, 'rb') as f:
    assert f.read() == binary_content
  
  # Test with encoding for string content
  encoded_content = "ñáéíóú"  # Non-ASCII characters
  encoded_file = BaseFile.from_content(
    content=encoded_content,
    base_directory=temp_dir,
    file_name="encoded_test.txt",
    encoding="utf-8"
  )
  
  assert encoded_file is not None
  assert encoded_file.file_exists() is True
  
  # Verify encoded content was written correctly
  with open(encoded_file.file_path, 'r', encoding='utf-8') as f:
    assert f.read() == encoded_content


def test_cleanup_deleted_files(temp_dir, monkeypatch):
  """Test cleaning up deleted files."""
  # Create mock manifest
  mock_manifest = MagicMock()
  mock_manifest.cleanup_files.return_value = ["file1", "file2"]
  mock_manifest.get_file_metadata.side_effect = lambda file_id: {
    "file1": {
      "is_reference": False,
      "subdirectory": "text"
    },
    "file2": {
      "is_reference": True,
      "subdirectory": "images"
    }
  }.get(file_id)
  
  with patch('files.base.FileManifest', return_value=mock_manifest):
    # Create test files
    file1_path = os.path.join(temp_dir, "text", "file1")
    os.makedirs(os.path.dirname(file1_path), exist_ok=True)
    with open(file1_path, "w") as f:
      f.write("test")
    
    # Run cleanup
    deleted_count = BaseFile.cleanup_deleted_files(temp_dir)
    
    # Should have deleted one file (file1)
    assert deleted_count == 1
    
    # Manifest's remove_file_metadata should be called for both files
    assert mock_manifest.remove_file_metadata.call_count == 2 