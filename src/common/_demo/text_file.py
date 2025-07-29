"""
TextFile demonstration functionality.
"""

from common.files.text import TextFile


# Demo content constant
TEXTFILE_DEMO_CONTENT = """
This is a sample text file for demonstration.
It contains multiple lines of text.
We can analyze statistics, search content, and more.

The TextFile class provides:
- Encoding detection
- Content statistics
- Text searching capabilities
- Preview generation
"""


class TextFileDemo:
  """Demo class for TextFile functionality."""

  def __init__(self, session_dir: str):
    """Initialize with session directory."""
    self.session_dir = session_dir

  def run(self):
    """Demonstrate TextFile functionality."""
    print("\n=== TextFile Demo ===")
    print("TextFile extends BaseFile with specialized text processing capabilities.")

    try:
      # Create a TextFile instance
      text_file = TextFile(
        base_directory=self.session_dir,
        file_name="demo_text_file.txt"
      )

      print(f"✓ Created TextFile: {text_file.file_name}")

      # Save demo content
      saved_path = text_file.save(content=TEXTFILE_DEMO_CONTENT)

      if saved_path:
        print(f"✓ File saved successfully to: {saved_path}")

        # Demonstrate text analysis capabilities
        stats = text_file.get_content_statistics()
        if stats:
          print("✓ Content statistics:")
          print(f"  - Character count: {stats.get('character_count')}")
          print(f"  - Line count: {stats.get('line_count')}")
          print(f"  - Word count: {stats.get('word_count')}")

        # Demonstrate search functionality
        search_results = text_file.search_content("demonstration")
        if search_results:
          print(f"✓ Found '{search_results['query']}' at:")
          for match in search_results['matches']:
            print(f"  - Line {match['line_number']}: {match['line_content'].strip()}")

        # Demonstrate preview generation
        preview = text_file.get_preview(max_chars=100)
        if preview:
          print(f"✓ Preview (100 chars): {preview['content']}")
          if preview['truncated']:
            print("  - Content was truncated")

        # Demonstrate encoding detection
        encoding_info = text_file.detect_encoding()
        if encoding_info:
          print(f"✓ Detected encoding: {encoding_info.get('encoding')}")
          print(f"  - Confidence: {encoding_info.get('confidence')}")

    except Exception as e:
      print(f"✗ Error in TextFile demo: {e}")
