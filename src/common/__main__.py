"""
Demo selector for the common module classes.
Allows user to select and test different common functionality.
"""

# External dependencies
import uuid
import os

# Internal dependencies
from common.files.base import BaseFile
from common.files.text import TextFile
from common.files.conversation.conversation import Conversation
from common.files.conversation.conversation_settings import ConversationSettings
from common.logger import initialize_logging
from common.results import Result
from common.files.manifest import FileManifest
from common.enums.conversation import MessageRole



########################################################################
#                              CONSTANTS                               #
########################################################################
# Directory structure constants
DEFAULT_STORAGE_DIR = "storage"
DEMOS_SUBDIR = "demos"

# Available demos
DEMOS = [
  "BaseFile Demo",
  "TextFile Demo",
  "Conversation Demo",
  "Logger Demo",
  "Result Demo",
  "FileManifest Demo"
]

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


########################################################################
#                              CLASSES                                 #
########################################################################
class CommonDemos:
  """Demo class for showcasing common module functionality."""

  def __init__(self):
    """Initialize with a structured directory for demos."""
    # Create unique demo session directory
    session_id = str(uuid.uuid4())[:8]  # Use first 8 chars of UUID

    # Build directory structure: storage/demos/{session_id}/
    self.base_dir = os.path.abspath(DEFAULT_STORAGE_DIR)
    self.demos_dir = os.path.join(self.base_dir, DEMOS_SUBDIR)
    self.session_dir = os.path.join(self.demos_dir, session_id)
    self.log_dir = os.path.join(self.session_dir, "log")

    # Create directories if they don't exist
    os.makedirs(self.session_dir, exist_ok=True)
    os.makedirs(self.log_dir, exist_ok=True)

    print(f"Demo session directory: {self.session_dir}")
    print(f"Log directory: {self.log_dir}")

  def cleanup(self):
    """Clean up demo files (optional - files are kept for inspection)."""
    print(f"\nDemo files are saved in: {self.session_dir}")
    print(f"Log files are saved in: {self.log_dir}")
    print("Files are kept for inspection. You can manually delete them if needed.")

  def demo_base_file(self):
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

  def demo_text_file(self):
    """Demonstrate TextFile functionality."""
    print("\n=== TextFile Demo ===")
    print("TextFile extends BaseFile with text-specific features.")

    try:
      # Create TextFile from string
      content = TEXTFILE_DEMO_CONTENT

      text_file = TextFile.from_string(
        content=content,
        base_directory=self.session_dir,
        file_name="demo_text_file.txt"
      )

      if text_file:
        print(f"✓ Created TextFile: {text_file.file_name}")

        # Get statistics
        stats = text_file.get_stats()
        print(f"✓ Text statistics:")
        print(f"  - Lines: {stats['line_count']}")
        print(f"  - Words: {stats['word_count']}")
        print(f"  - Characters: {stats['char_count']}")
        print(f"  - Encoding: {text_file.encoding}")

        # Get preview
        preview = text_file.get_preview(max_lines=3)
        print(f"✓ Preview (first 3 lines):")
        print(f"  {preview.replace(chr(10), chr(10)+'  ')}")

        # Search functionality
        search_results = text_file.search("TextFile", case_sensitive=False)
        print(f"✓ Search for 'TextFile': {len(search_results)} matches")
        for line_num, line_content in search_results:
          print(f"  - Line {line_num}: {line_content.strip()}")

        # Get specific lines
        lines = text_file.get_lines(start=1, end=3)
        print(f"✓ Lines 1-3: {len(lines)} lines retrieved")

    except Exception as e:
      print(f"✗ Error in TextFile demo: {e}")

  def demo_conversation(self):
    """Demonstrate Conversation functionality."""
    print("\n=== Conversation Demo ===")
    print("Conversation manages structured chat conversations with messages, actions, and tools.")

    try:
      # Create a conversation
      conversation = Conversation(
        base_directory=self.session_dir,
        file_name="demo_conversation",
        title="Demo Conversation",
        prompt="You are a helpful AI assistant demonstrating conversation functionality."
      )

      print(f"✓ Created Conversation: {conversation.title}")
      print(f"  - File: {conversation.file_name}")
      print(f"  - Prompt: {conversation.prompt}")

      # Add messages
      user_msg = conversation.add_message(
        role=MessageRole.USER,
        content="Hello! Can you tell me about the weather?",
        speaker="User"
      )
      print(f"✓ Added user message: {user_msg.message_id}")

      assistant_msg = conversation.add_message(
        role=MessageRole.ASSISTANT,
        content="I'd be happy to help with weather information! However, I don't have access to current weather data. You might want to check a weather service.",
        speaker="Assistant"
      )
      print(f"✓ Added assistant message: {assistant_msg.message_id}")

      # Add a tool definition
      tool_def = conversation.add_tool_definition(
        name="get_weather",
        description="Get current weather for a location",
        parameters={
          "type": "object",
          "properties": {
            "location": {"type": "string", "description": "The location to get weather for"}
          },
          "required": ["location"]
        }
      )
      print(f"✓ Added tool definition: {tool_def.name}")

      # Update settings
      settings = ConversationSettings()
      settings.text_settings["temperature"] = 0.7
      settings.text_settings["max_tokens"] = 1000
      conversation.update_settings(settings)
      print("✓ Updated conversation settings")

      # Save the conversation
      saved_path = conversation.save()
      if saved_path:
        print(f"✓ Conversation saved to: {saved_path}")

        # Show summary
        print(f"✓ Conversation summary:")
        print(f"  - Messages: {len(conversation.messages)}")
        print(f"  - Actions: {len(conversation.actions)}")
        print(f"  - Tool definitions: {len(conversation.tool_definitions)}")

    except Exception as e:
      print(f"✗ Error in Conversation demo: {e}")

  def demo_logger(self):
    """Demonstrate Logger functionality."""
    print("\n=== Logger Demo ===")
    print("Logger provides configurable logging for the CLAIA application.")

    try:
      # Test different log configurations
      print("✓ Testing different log configurations:")

      # Configure with DEBUG level and detailed format
      logger = initialize_logging("debug", "detailed")
      print("  - Configured with DEBUG level and detailed format")

      # Log some messages
      logger.debug("This is a debug message")
      logger.info("This is an info message")
      logger.warning("This is a warning message")
      logger.error("This is an error message")

      # Configure with WARNING level and simple format
      print("\n  - Reconfiguring with WARNING level and simple format")
      logger = initialize_logging("warning", "simple")

      logger.debug("This debug message won't show")
      logger.info("This info message won't show")
      logger.warning("This warning message will show")
      logger.error("This error message will show")

      # Test file logging
      log_file_path = os.path.join(self.log_dir, "demo.log")
      print(f"\n  - Testing file logging to: {log_file_path}")
      logger = initialize_logging("info", "standard", log_file_path)

      logger.info("This message goes to both console and file")
      logger.warning("This warning also goes to both outputs")

      if os.path.exists(log_file_path):
        with open(log_file_path, 'r') as f:
          log_content = f.read()
        print(f"✓ Log file created with {len(log_content.splitlines())} lines")

    except Exception as e:
      print(f"✗ Error in Logger demo: {e}")

  def demo_result(self):
    """Demonstrate Result functionality."""
    print("\n=== Result Demo ===")
    print("Result provides standardized success/error handling.")

    try:
      # Success result
      success_result = Result.ok("Operation completed successfully!")
      print(f"✓ Success result: {success_result}")
      print(f"  - Is success: {success_result.is_success()}")
      print(f"  - Data: {success_result.get_data()}")

      # Error result
      error_result = Result.fail("Something went wrong", {"error_code": 404})
      print(f"✓ Error result: {error_result}")
      print(f"  - Is error: {error_result.is_error()}")
      print(f"  - Message: {error_result.get_message()}")
      print(f"  - Data: {error_result.get_data()}")

      # Shutdown result
      shutdown_result = Result.shutdown("Application is shutting down", exit_code=1)
      print(f"✓ Shutdown result: {shutdown_result}")
      print(f"  - Should exit: {shutdown_result.is_exit()}")
      print(f"  - Exit code: {shutdown_result.get_exit_code()}")

      # Custom result
      custom_result = Result(
        success=True,
        data={"processed": 100, "errors": 0},
        message="Batch processing completed"
      )
      print(f"✓ Custom result: {custom_result}")
      print(f"  - Data: {custom_result.get_data()}")

    except Exception as e:
      print(f"✗ Error in Result demo: {e}")

  def demo_file_manifest(self):
    """Demonstrate FileManifest functionality."""
    print("\n=== FileManifest Demo ===")
    print("FileManifest manages metadata for files in the system.")

    try:
      # Create a FileManifest
      manifest = FileManifest(self.session_dir)
      print(f"✓ Created FileManifest for: {self.session_dir}")

      # Add some file entries
      file_metadata = {
        "file_id": "demo_file_1",
        "file_name": "demo1.txt",
        "mime_type": "text/plain",
        "size": 1024,
        "status": "active",
        "metadata": {"description": "Demo file 1"}
      }

      if manifest.add_file(file_metadata):
        print("✓ Added file metadata to manifest")

      # Add another file
      file_metadata2 = {
        "file_id": "demo_file_2",
        "file_name": "demo2.json",
        "mime_type": "application/json",
        "size": 512,
        "status": "active",
        "metadata": {"description": "Demo file 2", "type": "config"}
      }

      if manifest.add_file(file_metadata2):
        print("✓ Added second file metadata to manifest")

      # Get all files
      all_files = manifest.get_all_files()
      print(f"✓ Retrieved all files: {len(all_files)} entries")
      for file_id, metadata in all_files.items():
        print(f"  - {file_id}: {metadata.get('file_name')} ({metadata.get('mime_type')})")

      # Get specific file
      file_info = manifest.get_file("demo_file_1")
      if file_info:
        print(f"✓ Retrieved specific file: {file_info['file_name']}")

      # Update file metadata
      if manifest.update_file("demo_file_1", {"last_accessed": "2024-01-01"}):
        print("✓ Updated file metadata")

      # Save manifest
      if manifest.save():
        print("✓ Manifest saved successfully")

    except Exception as e:
      print(f"✗ Error in FileManifest demo: {e}")


def display_menu() -> None:
  """Display the available demos menu."""
  print("\n" + "="*50)
  print("CLAIA Common Module Demo Selector")
  print("="*50)

  for i, demo in enumerate(DEMOS, 1):
    print(f"{i}. {demo}")

  print("0. Exit")
  print("="*50)


def get_user_selection() -> str:
  """
  Get user selection from the menu.

  Returns:
    The selected demo name, or empty string to exit
  """
  while True:
    try:
      choice = input("\nEnter your choice (0-{}): ".format(len(DEMOS)))

      if choice == "0":
        return ""

      choice_num = int(choice)
      if 1 <= choice_num <= len(DEMOS):
        return DEMOS[choice_num - 1]
      else:
        print(f"Invalid choice. Please enter a number between 0 and {len(DEMOS)}.")

    except ValueError:
      print("Invalid input. Please enter a number.")
    except KeyboardInterrupt:
      print("\nExiting...")
      return ""


def handle_demo_selection(selected_demo: str, demos: CommonDemos) -> None:
  """
  Handle the selected demo by running the appropriate demonstration.

  Args:
    selected_demo: The name of the selected demo
    demos: The CommonDemos instance
  """
  print(f"\nRunning demo: {selected_demo}")
  print("-" * 50)

  try:
    demo_map = {
      "BaseFile Demo": demos.demo_base_file,
      "TextFile Demo": demos.demo_text_file,
      "Conversation Demo": demos.demo_conversation,
      "Logger Demo": demos.demo_logger,
      "Result Demo": demos.demo_result,
      "FileManifest Demo": demos.demo_file_manifest
    }

    if selected_demo in demo_map:
      demo_map[selected_demo]()
    else:
      print(f"Demo not implemented: {selected_demo}")

  except Exception as e:
    print(f"Error running demo {selected_demo}: {e}")

  print("-" * 50)


def main() -> None:
  """Main function to run the demo selector."""
  print("Welcome to the CLAIA Common Module Demo!")
  print("This demonstrates the core functionality of the common module classes.")

  # Initialize demos
  demos = CommonDemos()

  try:
    while True:
      display_menu()
      selected_demo = get_user_selection()

      if not selected_demo:
        print("Goodbye!")
        break

      handle_demo_selection(selected_demo, demos)

  finally:
    # Always clean up
    demos.cleanup()


if __name__ == "__main__":
  main()
