"""
Prompt demonstration functionality.
"""

import json
from common.files.prompt import Prompt


class PromptDemo:
  """Demo class for Prompt functionality."""

  def __init__(self, session_dir: str):
    """Initialize with session directory."""
    self.session_dir = session_dir

  def run(self):
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
