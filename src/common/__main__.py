"""
Demo selector for the common module classes.
Allows user to select and test different common functionality.
"""

# External dependencies
import logging
import uuid
import os

# Internal dependencies
from common.files.base import BaseFile
from common.files.text import TextFile
from common.files.conversation.conversation import Conversation
from common.files.conversation.conversation_settings import ConversationSettings
from common.files.prompt import Prompt
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
  "Prompt Demo",
  "Conversation Demo",
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

    # Create directories if they don't exist
    os.makedirs(self.session_dir, exist_ok=True)

    # Initialize logging for demos
    self.logger = logging.getLogger(__name__)

    print(f"Demo session directory: {self.session_dir}")
    self.logger.info(f"Demo session initialized: {session_id}")

  def cleanup(self):
    """Clean up demo files (optional - files are kept for inspection)."""
    print(f"\nDemo files are saved in: {self.session_dir}")
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

  def demo_prompt(self):
    """Demonstrate Prompt functionality."""
    print("\n=== Prompt Demo ===")
    print("Prompt manages AI prompts with JSON storage and name validation.")

    try:
      # 1. Demonstrate prompt name validation
      print("\n1. Prompt Name Validation:")
      test_names = ["My Cool Prompt", "ASSISTANT_PROMPT", "chat-bot!", "  multiple---spaces  "]
      for name in test_names:
        validated = Prompt.validate_prompt_name(name)
        print(f"  '{name}' -> '{validated}'")

      # 2. Create a prompt using create_prompt class method
      print("\n2. Creating Prompt with create_prompt():")
      prompt_text = """You are a helpful AI assistant.

User Query: {query}
Context: {context}

Please provide a clear and helpful response."""

      prompt = Prompt.create_prompt(
        base_directory=self.session_dir,
        prompt_name="Demo Assistant Prompt",
        prompt_text=prompt_text
      )

      if prompt:
        print(f"✓ Created Prompt: {prompt.file_name}")
        print(f"  - Prompt Name: {prompt.prompt_name}")
        print(f"  - File ID: {prompt.file_id}")
        print(f"  - Internal Path: {prompt.get_internal_path()}")
        print(f"  - MIME Type: {prompt.mime_type}")

      # 3. Demonstrate manual prompt creation
      print("\n3. Manual Prompt Creation:")
      manual_prompt = Prompt(
        base_directory=self.session_dir,
        prompt_name="manual test prompt",
        prompt_text="This is a manually created prompt for testing.",
        file_name="custom_prompt_name"  # Will become custom_prompt_name.json
      )

      saved_path = manual_prompt.save()
      if saved_path:
        print(f"✓ Manual prompt saved: {manual_prompt.file_name}")
        print(f"  - Validated name: {manual_prompt.prompt_name}")
        print(f"  - Saved to: {saved_path}")

      # 4. Demonstrate loading prompts
      print("\n4. Loading Prompt by Name:")
      loaded_prompt = Prompt.load_prompt(
        prompt_name="demo-assistant-prompt.json",  # This should match the validated name
        base_directory=self.session_dir
      )

      if loaded_prompt:
        print(f"✓ Loaded prompt: {loaded_prompt.prompt_name}")
        print(f"  - File: {loaded_prompt.file_name}")
        print(f"  - Text preview: {loaded_prompt.prompt_text[:50]}...")
      else:
        print("✗ Failed to load prompt (this might be expected if name doesn't match)")

      # 5. Show metadata and content inspection
      print("\n5. Metadata and Content:")
      if prompt:
        # Get metadata
        metadata = prompt.to_dict()
        print(f"✓ Prompt metadata fields: {list(metadata.keys())}")
        print(f"  - Prompt name in metadata: {metadata.get('metadata', {}).get('prompt_name')}")

        # Show content structure (since it's JSON)
        content = prompt._get_default_content()
        if content:
          print(f"✓ Default JSON content structure:")
          import json
          try:
            parsed = json.loads(content)
            for key, value in parsed.items():
              preview = str(value)[:30] + "..." if len(str(value)) > 30 else str(value)
              print(f"  - {key}: {preview}")
          except json.JSONDecodeError:
            print("  - Content is not valid JSON")

      # 6. Demonstrate text file inherited functionality
      print("\n6. TextFile Inherited Features:")
      if prompt:
        # Since Prompt inherits from TextFile, show text stats
        if hasattr(prompt, 'get_stats'):
          stats = prompt.get_stats()
          print(f"✓ Text statistics available: {list(stats.keys())}")

        # Show file operations
        print(f"✓ File operations:")
        print(f"  - File exists: {prompt.exists()}")
        print(f"  - File size: {prompt.get_file_size()} bytes")
        print(f"  - Subdirectory: {prompt.get_subdirectory()}")

    except Exception as e:
      print(f"✗ Error in Prompt demo: {e}")

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
      "Prompt Demo": demos.demo_prompt,
      "Conversation Demo": demos.demo_conversation,
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
