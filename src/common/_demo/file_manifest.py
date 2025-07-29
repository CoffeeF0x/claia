"""
FileManifest demonstration functionality.
"""

from common.files.base import BaseFile
from common.files.text import TextFile
from common.files.manifest import FileManifest


class FileManifestDemo:
  """Demo class for FileManifest functionality."""

  def __init__(self, session_dir: str):
    """Initialize with session directory."""
    self.session_dir = session_dir

  def run(self):
    """Demonstrate FileManifest functionality."""
    print("\n=== FileManifest Demo ===")
    print("FileManifest manages metadata for files in the system using BaseFile objects.")

    try:
      # Create a FileManifest
      manifest = FileManifest(self.session_dir)
      print(f"✓ Created FileManifest for: {self.session_dir}")

      # Create actual BaseFile objects to demonstrate the new interface
      demo_file1 = BaseFile(
        base_directory=self.session_dir,
        file_name="demo_manifest_file1.txt"
      )
      demo_file1.metadata["description"] = "Demo file 1 for manifest"
      demo_file1.metadata["category"] = "demo"

      # Save the file with some content
      demo_file1.save(content="This is demo file 1 content for manifest testing.")
      print(f"✓ Created demo file 1: {demo_file1.file_name}")

      # Add file to manifest using new interface
      if manifest.add(demo_file1):
        print("✓ Added file 1 to manifest using new add() method")

      # Create second file
      demo_file2 = TextFile(
        base_directory=self.session_dir,
        file_name="demo_manifest_file2.txt"
      )
      demo_file2.metadata["description"] = "Demo text file 2"
      demo_file2.metadata["type"] = "text"
      demo_file2.save(content="This is demo text file 2 content.\nIt has multiple lines.")
      print(f"✓ Created demo file 2: {demo_file2.file_name}")

      # Add second file to manifest
      if manifest.add(demo_file2):
        print("✓ Added file 2 to manifest using new add() method")

      # Update file metadata
      demo_file1.metadata["last_accessed"] = "2024-01-01"
      if manifest.update(demo_file1):
        print("✓ Updated file 1 metadata using new update() method")

      # Get all files
      all_files = manifest.get_all_files()
      print(f"✓ Retrieved all files: {len(all_files)} entries")
      for file_id, metadata in all_files.items():
        print(f"  - {file_id}: {metadata.get('file_name')} ({metadata.get('mime_type')})")

      # Demonstrate search functionality
      search_results = manifest.find_files_by_criteria(
        metadata_filters={"category": "demo"}
      )
      print(f"✓ Found {len(search_results)} files with category='demo'")

      # Demonstrate deletion marking
      if manifest.delete(demo_file2):
        print("✓ Marked file 2 for deletion using new delete() method")

      # Show cleanup functionality
      print("✓ Cleanup functionality available via permanently_delete_files()")
      print("  (Not running actual cleanup in demo)")

      # Save manifest
      if manifest._save_manifest():
        print("✓ Manifest saved successfully")

    except Exception as e:
      print(f"✗ Error in FileManifest demo: {e}")
