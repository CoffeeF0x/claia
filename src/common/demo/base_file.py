"""
BaseFile demonstration functionality.
"""

from common.files.base import BaseFile


class BaseFileDemo:
  """Demo class for BaseFile functionality."""

  def __init__(self, session_dir: str):
    """Initialize with session directory."""
    self.session_dir = session_dir

  def run(self):
    """Demonstrate BaseFile functionality."""
    print("\n=== BaseFile Demo ===")
    print("BaseFile is the foundation class for all file operations in CLAIA.")

    try:
      # Create a BaseFile instance
      base_file = BaseFile(
        base_directory=self.session_dir,
        file_name="demo_base_file.txt"
      )

      print(f"✓ Created BaseFile: {base_file.file_name}")
      print(f"  - File ID: {base_file.file_id}")
      print(f"  - MIME Type: {base_file.mime_type}")
      print(f"  - Internal Path: {base_file.get_internal_path()}")

      # Test directory creation
      if base_file.ensure_directory_exists():
        print("✓ Directory structure created successfully")

      # Save some content
      content = "This is a demo file created by BaseFile.\nIt demonstrates basic file operations."
      saved_path = base_file.save(content=content)

      if saved_path:
        print(f"✓ File saved successfully to: {saved_path}")
        print(f"  - File exists: {base_file.exists()}")
        print(f"  - File size: {base_file.get_file_size()} bytes")

      # Demonstrate metadata
      base_file.metadata["demo_info"] = "This is a demonstration file"
      if base_file.save_metadata():
        print("✓ Metadata saved successfully")
        print(f"  - Metadata: {base_file.to_dict()}")

    except Exception as e:
      print(f"✗ Error in BaseFile demo: {e}")
