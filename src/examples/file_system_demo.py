"""
CLAIA File System Demo

This script demonstrates how to use the CLAIA file system in a real-world scenario.
It shows common file operations with both regular and image files.
"""

# External dependencies
import os
import shutil
import tempfile
import sys
import time
from pathlib import Path

# Add the src directory to the path so we can import our modules
src_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(src_dir))

# Internal dependencies
from files import BaseFile, ImageFile, FileManifest, TextFile
from enums import FileStatus


########################################################################
#                              CONSTANTS                               #
########################################################################
REFERENCE_URL = "https://example.com/sample.jpg"
DOWNLOAD_URL = "https://lloydbower.com/favicon.png"



########################################################################
#                             SETUP DEMO                               #
########################################################################
def setup_demo():
  """Set up the demo environment."""
  print("Setting up demo environment...")
  
  # Create a temp directory for our demo
  base_dir = tempfile.mkdtemp(prefix="claia_demo_")
  print(f"Demo files will be stored in: {base_dir}")
  
  # Create some sample files
  text_file = os.path.join(base_dir, "sample.txt")
  with open(text_file, "w") as f:
    f.write("This is a sample text file for the CLAIA file system demo.")
  
  # Create a simple image if PIL is available
  image_file = None
  try:
    from PIL import Image
    image_file = os.path.join(base_dir, "sample.png")
    img = Image.new('RGB', (200, 100), color='blue')
    img.save(image_file)
    print("Created sample text and image files")
  except ImportError:
    print("Created sample text file (PIL not available for image creation)")
  
  # Create a markdown file for text file demo
  markdown_file = os.path.join(base_dir, "sample.md")
  with open(markdown_file, "w") as f:
    f.write("# Sample Markdown Document\n\n")
    f.write("This is a sample document with multiple lines.\n")
    f.write("It demonstrates the TextFile class functionality.\n\n")
    f.write("## Features\n\n")
    f.write("- Line counting\n")
    f.write("- Word counting\n")
    f.write("- Character counting\n")
    f.write("- Text searching\n")
    f.write("- Content preview\n\n")
    f.write("## Code Example\n\n")
    f.write("```python\n")
    f.write("def sample_function():\n")
    f.write("    print('Hello, CLAIA!')\n")
    f.write("```\n")
  
  # Create export directory
  export_dir = os.path.join(base_dir, "exports")
  os.makedirs(export_dir, exist_ok=True)
  
  return base_dir, text_file, image_file, markdown_file, export_dir



########################################################################
#                           REGULAR FILES                              #
########################################################################
def demo_regular_files(base_dir, sample_file, export_dir):
  """Demonstrate operations with regular files."""
  print("\n" + "-" * 70)
  print("REGULAR FILE OPERATIONS")
  print("-" * 70)
  
  # Create a file object from a path
  print("\n1. Creating and saving a file")
  file = BaseFile.from_source(sample_file, base_dir)
  saved_path = file.save()
  print(f"   - Created file with ID: {file.file_id}")
  print(f"   - Saved to: {saved_path}")
  
  # Add references to the file
  print("\n2. Adding references to the file")
  conversation_ref = "conversation_123"
  message_ref = "message_456"
  file.add_reference(conversation_ref)
  file.add_reference(message_ref)
  print(f"   - Added references: {conversation_ref}, {message_ref}")
  
  # Load the file again
  print("\n3. Loading the file by ID")
  loaded_file = BaseFile.load(file.file_id, base_dir)
  manifest = FileManifest(base_dir)
  metadata = manifest.get_file_metadata(file.file_id)
  print(f"   - File name: {loaded_file.file_name}")
  print(f"   - References: {metadata['references']}")
  
  # Export the file
  print("\n4. Exporting the file to an external location")
  export_path = os.path.join(export_dir, "exported_text.txt")
  result = file.export(export_path)
  print(f"   - Exported to: {export_path}")
  print(f"   - Export successful: {result}")
  
  # Try to export again (should fail without force)
  result = file.export(export_path)
  print(f"   - Export to existing path without force: {result}")
  
  # Export with force_overwrite
  result = file.export(export_path, force_overwrite=True)
  print(f"   - Export with force_overwrite: {result}")
  
  # Remove a reference
  print("\n5. Removing a reference")
  file.remove_reference(conversation_ref)
  metadata = manifest.get_file_metadata(file.file_id)
  print(f"   - References after removal: {metadata['references']}")
  
  # Mark for deletion
  print("\n6. Marking the file for deletion")
  file.mark_for_deletion()
  metadata = manifest.get_file_metadata(file.file_id)
  print(f"   - File status after marking: {metadata['status']}")
  
  # Get files ready for cleanup
  print("\n7. Finding files ready for cleanup")
  cleanup_files = manifest.cleanup_files(older_than_days=0)
  print(f"   - Files ready for cleanup: {len(cleanup_files)}")
  
  # Clean up deleted files
  print("\n8. Cleaning up deleted files")
  deleted_count = BaseFile.cleanup_deleted_files(base_dir, older_than_days=0)
  print(f"   - Deleted files: {deleted_count}")
  
  # In the regular_files demo function, add this section after the existing code
  print("\n9. Creating a file from URL (reference)")
  url_file = BaseFile.from_source(REFERENCE_URL, base_dir)
  print(f"   - Created URL reference file with ID: {url_file.file_id}")
  print(f"   - Is reference: {url_file.is_reference}")
  print(f"   - File name: {url_file.file_name}")
  
  # Demo the unified from_source method with custom filename
  print("\n10. Unified from_source method with custom filename")
  custom_name_file = BaseFile.from_source(
    source=sample_file,
    base_directory=base_dir,
    file_name="custom_named_file.txt"
  )
  print(f"   - Created file with custom name: {custom_name_file.file_name}")
  print(f"   - Original file basename: {os.path.basename(sample_file)}")
  
  # Try to download a real URL (conditionally)
  try:
    import requests
    print("\n11. Downloading content from URL (non-reference)")
    try:
      download_file = BaseFile.from_source(
        source=DOWNLOAD_URL,
        base_directory=base_dir,
        is_reference=False  # Force download instead of reference
      )
      if download_file:
        print(f"   - Downloaded file with ID: {download_file.file_id}")
        print(f"   - File size: {download_file.get_file_size()} bytes")
        
        # Export the downloaded image
        print("\n12. Exporting downloaded image")
        export_path = os.path.join(export_dir, "downloaded_image.png")
        export_result = download_file.export(export_path)
        print(f"   - Exported to: {export_path}")
        print(f"   - Export successful: {export_result}")
      else:
        print("   - Download failed - see logs for details")
    except Exception as e:
      print(f"   - Download error: {e}")
  except ImportError:
    print("\n11. Skipping URL download demo (requests library not available)")
  
  return file.file_id



########################################################################
#                            IMAGE FILES                               #
########################################################################
def demo_image_files(base_dir, sample_image, export_dir):
  """Demonstrate operations with image files."""
  if not sample_image:
    print("\nSkipping image demo (PIL not available)")
    return None
  
  print("\n" + "-" * 70)
  print("IMAGE FILE OPERATIONS")
  print("-" * 70)
  
  # Create an image file
  print("\n1. Creating and processing an image file")
  image = ImageFile.from_source(sample_image, base_dir)
  image.save()
  metadata = image.process()
  print(f"   - Image ID: {image.file_id}")
  print(f"   - Dimensions: {image.width}x{image.height}")
  print(f"   - Format: {image.format}")
  
  # Get base64 representation
  print("\n2. Generating base64 representation")
  base64_data = image.get_base64()
  preview = base64_data[:50] + "..." if base64_data else "None"
  print(f"   - Base64 preview: {preview}")
  
  # Export the image
  print("\n3. Exporting the image")
  export_path = os.path.join(export_dir, "exported_image.png")
  result = image.export(export_path)
  print(f"   - Exported to: {export_path}")
  print(f"   - Export successful: {result}")
  
  # Convert the image
  print("\n4. Converting to different format")
  jpeg_image = image.convert("jpeg", quality=95)
  if jpeg_image:
    print(f"   - Converted image ID: {jpeg_image.file_id}")
    print(f"   - New format: {jpeg_image.format}")
    
    # Export the converted image
    jpeg_export_path = os.path.join(export_dir, "exported_image.jpg")
    jpeg_image.export(jpeg_export_path)
    print(f"   - Exported JPEG to: {jpeg_export_path}")
  
  # Resize the image
  print("\n5. Resizing the image")
  resized_image = image.resize(100, 50, keep_aspect_ratio=True)
  if resized_image:
    resized_image.process()  # Update metadata
    print(f"   - Resized image ID: {resized_image.file_id}")
    print(f"   - New dimensions: {resized_image.width}x{resized_image.height}")
    
    # Export the resized image
    resized_export_path = os.path.join(export_dir, "exported_image_small.png")
    resized_image.export(resized_export_path)
    print(f"   - Exported resized image to: {resized_export_path}")
  
  # Create external reference
  print("\n6. Creating external reference to image")
  ref_image = ImageFile.from_source(sample_image, base_dir, is_reference=True)
  ref_image.save()
  print(f"   - Reference image ID: {ref_image.file_id}")
  print(f"   - Is reference: {ref_image.is_reference}")
  print(f"   - Status: {ref_image.status.name}")
  
  return image.file_id



########################################################################
#                            TEXT FILES                                #
########################################################################
def demo_text_files(base_dir, markdown_file, export_dir):
  """Demonstrate operations with specialized text files."""
  print("\n" + "-" * 70)
  print("TEXT FILE OPERATIONS")
  print("-" * 70)
  
  # Create a text file from markdown
  print("\n1. Creating and processing a text file from path")
  text_file = TextFile.from_source(markdown_file, base_dir)
  text_file.save()
  print(f"   - Text file ID: {text_file.file_id}")
  print(f"   - MIME type: {text_file.mime_type}")
  
  # Create a text file from string content
  print("\n2. Creating a text file from string content")
  content = """# In-Memory Text Content
  
This text file was created directly from a string in memory.
No temporary files or manual file operations needed!

## Features
- Easy creation from strings
- Automatic statistics calculation
- Full text processing support

## Example Code
```python
text = TextFile.from_string(content, base_dir, "memory_text.txt")
```
"""
  memory_text = TextFile.from_string(content, base_dir, "memory_text.txt")
  print(f"   - Memory text file ID: {memory_text.file_id}")
  print(f"   - File exists: {memory_text.file_exists()}")
  
  # Create a text file without specifying a filename
  print("\n3. Creating a text file without a file name")
  auto_named_content = "This text file was created without specifying a file name.\nThe file_name defaults to the file_id."
  auto_named_text = TextFile.from_string(auto_named_content, base_dir)
  print(f"   - Auto-named text file ID: {auto_named_text.file_id}")
  print(f"   - File name: {auto_named_text.file_name}")
  print(f"   - File exists: {auto_named_text.file_exists()}")
  
  # Get text statistics for the memory file
  stats = memory_text.get_stats()
  print(f"   - Line count: {stats['line_count']}")
  print(f"   - Word count: {stats['word_count']}")
  print(f"   - Character count: {stats['char_count']}")
  
  # Get text statistics
  print("\n4. Analyzing text content")
  stats = text_file.get_stats()
  print(f"   - Line count: {stats['line_count']}")
  print(f"   - Word count: {stats['word_count']}")
  print(f"   - Character count: {stats['char_count']}")
  
  # Get a content preview
  print("\n5. Generating content preview")
  preview = text_file.get_preview(max_lines=5)
  print(f"   - Preview (first 5 lines):")
  for line in preview.splitlines()[:5]:
    print(f"     | {line}")
  
  # Search for content
  print("\n6. Searching text content")
  search_results = text_file.search("sample", case_sensitive=False)
  print(f"   - Found {len(search_results)} matches for 'sample':")
  for i, (line_num, line_content) in enumerate(search_results[:3], 1):
    preview = line_content[:40] + "..." if len(line_content) > 40 else line_content
    print(f"     {i}. Line {line_num}: {preview}")
  
  if len(search_results) > 3:
    print(f"     ... and {len(search_results) - 3} more matches")
  
  # Extract specific lines
  print("\n7. Extracting specific content")
  code_lines = text_file.get_lines(start=13, end=16)  # Sample code section
  print(f"   - Code section (lines 13-16):")
  for line in code_lines:
    print(f"     | {line}")
  
  # Update the memory file with new content
  print("\n8. Modifying text file content")
  original_stats = memory_text.get_stats()
  new_content = memory_text.get_content() + "\n\nThis line was added dynamically!"
  memory_text.save(content=new_content)
  new_stats = memory_text.get_stats()
  print(f"   - Original line count: {original_stats['line_count']}")
  print(f"   - New line count: {new_stats['line_count']}")
  print(f"   - Content updated successfully")
  
  # Export the text file
  print("\n9. Exporting the text files")
  export_path = os.path.join(export_dir, "exported_markdown.md")
  result = text_file.export(export_path)
  print(f"   - Exported file to: {export_path}")
  print(f"   - Export successful: {result}")
  
  memory_export_path = os.path.join(export_dir, "exported_memory_text.md")
  result = memory_text.export(memory_export_path)
  print(f"   - Exported memory file to: {memory_export_path}")
  print(f"   - Export successful: {result}")
  
  return text_file.file_id



########################################################################
#                               MAIN                                   #
########################################################################
def main():
  """Run the demo."""
  # Set up the demo
  base_dir, sample_file, sample_image, markdown_file, export_dir = setup_demo()
  
  try:
    # Demonstrate regular file operations
    file_id = demo_regular_files(base_dir, sample_file, export_dir)
    
    # Demonstrate image file operations
    image_id = demo_image_files(base_dir, sample_image, export_dir)
    
    # Demonstrate text file operations
    text_id = demo_text_files(base_dir, markdown_file, export_dir)
    
    # Show final file manifest state
    print("\n" + "-" * 70)
    print("FINAL MANIFEST STATE")
    print("-" * 70)
    
    manifest = FileManifest(base_dir)
    all_files = manifest.get_all_files()
    
    if not all_files:
      print("\nManifest is empty (all files cleaned up)")
    else:
      print(f"\nManifest contains {len(all_files)} files:")
      for file_id, metadata in all_files.items():
        print(f"  - {file_id}: {metadata['file_name']} ({metadata['status']})")
    
    # List exported files
    print("\n" + "-" * 70)
    print("EXPORTED FILES")
    print("-" * 70)
    
    exported_files = os.listdir(export_dir)
    print(f"\nExported {len(exported_files)} files:")
    for filename in exported_files:
      file_path = os.path.join(export_dir, filename)
      file_size = os.path.getsize(file_path)
      print(f"  - {filename} ({file_size} bytes)")
  
  finally:
    # Clean up the demo directory
    print("\nCleaning up demo environment...")
    if os.path.exists(base_dir):
      shutil.rmtree(base_dir)
    print("Demo completed!")


if __name__ == "__main__":
  main() 