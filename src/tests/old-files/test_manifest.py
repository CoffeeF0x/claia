"""
Tests for the FileManifest class.
"""

# External dependencies
import os
from datetime import datetime, timedelta

# Internal dependencies
from files import FileManifest
from enums import FileStatus



########################################################################
#                             MANIFEST TESTS                           #
########################################################################
def test_singleton_behavior(temp_dir):
  """Test that FileManifest behaves as a singleton."""
  # Reset before test to ensure clean state
  FileManifest._instance = None

  manifest1 = FileManifest(temp_dir)
  manifest2 = FileManifest(temp_dir)

  # Same instance
  assert manifest1 is manifest2

  # Different base_directory doesn't create new instance
  another_dir = os.path.join(temp_dir, "another")
  manifest3 = FileManifest(another_dir)
  assert manifest1 is manifest3


def test_update_and_get_metadata(clean_manifest):
  """Test updating and retrieving file metadata."""
  file_id = "test_file_1"
  metadata = {
    "file_id": file_id,
    "file_name": "test.txt",
    "mime_type": "text/plain",
    "status": FileStatus.ACTIVE.name
  }

  # Update metadata
  result = clean_manifest.update_file_metadata(file_id, metadata)
  assert result is True

  # Get metadata
  retrieved = clean_manifest.get_file_metadata(file_id)
  assert retrieved is not None
  assert retrieved["file_id"] == file_id
  assert retrieved["file_name"] == "test.txt"


def test_remove_metadata(clean_manifest):
  """Test removing file metadata."""
  file_id = "test_file_2"
  metadata = {
    "file_id": file_id,
    "file_name": "test2.txt"
  }

  # Add and then remove metadata
  clean_manifest.update_file_metadata(file_id, metadata)
  result = clean_manifest.remove_file_metadata(file_id)
  assert result is True

  # Metadata should be gone
  retrieved = clean_manifest.get_file_metadata(file_id)
  assert retrieved is None


def test_get_all_files(clean_manifest):
  """Test retrieving all files from manifest."""
  # Add several files
  clean_manifest.update_file_metadata("file1", {"file_id": "file1", "type": "text"})
  clean_manifest.update_file_metadata("file2", {"file_id": "file2", "type": "image"})
  clean_manifest.update_file_metadata("file3", {"file_id": "file3", "type": "audio"})

  # Get all files
  all_files = clean_manifest.get_all_files()
  assert len(all_files) == 3
  assert "file1" in all_files
  assert "file2" in all_files
  assert "file3" in all_files


def test_get_files_by_status(clean_manifest):
  """Test retrieving files by status."""
  # Add files with different statuses
  clean_manifest.update_file_metadata("active1", {"file_id": "active1", "status": FileStatus.ACTIVE.name})
  clean_manifest.update_file_metadata("active2", {"file_id": "active2", "status": FileStatus.ACTIVE.name})
  clean_manifest.update_file_metadata("deleted", {"file_id": "deleted", "status": FileStatus.DELETED.name})
  clean_manifest.update_file_metadata("external", {"file_id": "external", "status": FileStatus.EXTERNAL.name})

  # Get files by status
  active_files = clean_manifest.get_files_by_status(FileStatus.ACTIVE)
  deleted_files = clean_manifest.get_files_by_status(FileStatus.DELETED)
  external_files = clean_manifest.get_files_by_status(FileStatus.EXTERNAL)

  assert len(active_files) == 2
  assert "active1" in active_files
  assert "active2" in active_files

  assert len(deleted_files) == 1
  assert "deleted" in deleted_files

  assert len(external_files) == 1
  assert "external" in external_files


def test_add_and_remove_references(clean_manifest):
  """Test adding and removing references to files."""
  file_id = "test_file"
  clean_manifest.update_file_metadata(file_id, {
    "file_id": file_id,
    "references": []
  })

  # Add references
  result1 = clean_manifest.add_reference(file_id, "ref1")
  result2 = clean_manifest.add_reference(file_id, "ref2")
  assert result1 is True
  assert result2 is True

  # Check references were added
  metadata = clean_manifest.get_file_metadata(file_id)
  assert "ref1" in metadata["references"]
  assert "ref2" in metadata["references"]

  # Remove reference
  result3 = clean_manifest.remove_reference(file_id, "ref1")
  assert result3 is True

  # Check reference was removed
  metadata = clean_manifest.get_file_metadata(file_id)
  assert "ref1" not in metadata["references"]
  assert "ref2" in metadata["references"]


def test_mark_for_deletion(clean_manifest):
  """Test marking a file for deletion."""
  file_id = "to_delete"
  clean_manifest.update_file_metadata(file_id, {
    "file_id": file_id,
    "status": FileStatus.ACTIVE.name
  })

  # Mark for deletion
  result = clean_manifest.mark_for_deletion(file_id)
  assert result is True

  # Check status was updated
  metadata = clean_manifest.get_file_metadata(file_id)
  assert metadata["status"] == FileStatus.DELETED.name
  assert "deletion_timestamp" in metadata


def test_get_unreferenced_files(clean_manifest):
  """Test getting unreferenced files."""
  # Add files with and without references
  clean_manifest.update_file_metadata("ref_file", {
    "file_id": "ref_file",
    "status": FileStatus.ACTIVE.name,
    "references": ["something"]
  })

  clean_manifest.update_file_metadata("unref_file1", {
    "file_id": "unref_file1",
    "status": FileStatus.ACTIVE.name,
    "references": []
  })

  clean_manifest.update_file_metadata("unref_file2", {
    "file_id": "unref_file2",
    "status": FileStatus.ACTIVE.name
  })

  # Add a deleted unreferenced file (shouldn't be returned)
  clean_manifest.update_file_metadata("deleted_unref", {
    "file_id": "deleted_unref",
    "status": FileStatus.DELETED.name,
    "references": []
  })

  # Get unreferenced files
  unreferenced = clean_manifest.get_unreferenced_files()
  assert len(unreferenced) == 2
  assert "unref_file1" in unreferenced
  assert "unref_file2" in unreferenced
  assert "ref_file" not in unreferenced
  assert "deleted_unref" not in unreferenced


def test_cleanup_files(clean_manifest, monkeypatch):
  """Test cleaning up deleted files based on age."""
  now = datetime.now()

  # Mock datetime.now() to return a fixed time
  class MockDatetime(datetime):
    @classmethod
    def now(cls):
      return now

  monkeypatch.setattr("files.manifest.datetime", MockDatetime)

  # Add files deleted at different times
  old_timestamp = (now - timedelta(days=40)).isoformat()
  recent_timestamp = (now - timedelta(days=10)).isoformat()

  clean_manifest.update_file_metadata("old_deleted", {
    "file_id": "old_deleted",
    "status": FileStatus.DELETED.name,
    "deletion_timestamp": old_timestamp
  })

  clean_manifest.update_file_metadata("recent_deleted", {
    "file_id": "recent_deleted",
    "status": FileStatus.DELETED.name,
    "deletion_timestamp": recent_timestamp
  })

  clean_manifest.update_file_metadata("no_timestamp", {
    "file_id": "no_timestamp",
    "status": FileStatus.DELETED.name
  })

  clean_manifest.update_file_metadata("active_file", {
    "file_id": "active_file",
    "status": FileStatus.ACTIVE.name
  })

  # Cleanup files older than 30 days
  cleanup_list = clean_manifest.cleanup_files(older_than_days=30)

  # Should include old_deleted and no_timestamp but not recent_deleted or active_file
  assert len(cleanup_list) == 2
  assert "old_deleted" in cleanup_list
  assert "no_timestamp" in cleanup_list
  assert "recent_deleted" not in cleanup_list
  assert "active_file" not in cleanup_list