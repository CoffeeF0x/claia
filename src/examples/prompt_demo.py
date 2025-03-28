"""
CLAIA Prompt File Demo

This script demonstrates how to use the CLAIA Prompt class.
"""

# External dependencies
import os
import sys
import json
import shutil
import tempfile
from pathlib import Path

# Add the src directory to the path so we can import our modules
src_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(src_dir))

# Internal dependencies
from files import Prompt



########################################################################
#                              CONSTANTS                               #
########################################################################
SAMPLE_PROMPTS = [
  {
    "name": "Simple Greeting",
    "prompt": "Hello, my name is {{name}}. I am {{age}} years old."
  },
  {
    "name": "Customer Service",
    "prompt": "I'm sorry to hear about your issue with {{product}}. Let me help you resolve this problem. Could you please provide more details about what happened?"
  },
  {
    "name": "Code Review",
    "prompt": "Please review the following {{language}} code and provide feedback:\n\n```{{language}}\n{{code}}\n```"
  }
]



########################################################################
#                             SETUP DEMO                               #
########################################################################
def setup_demo():
  """Set up the demo environment."""
  print("Setting up demo environment...")
  
  # Create a temp directory for our demo
  base_dir = tempfile.mkdtemp(prefix="claia_prompt_demo_")
  print(f"Demo files will be stored in: {base_dir}")
  
  return base_dir



########################################################################
#                             PROMPT FILES                             #
########################################################################
def demo_prompt_files(base_dir):
  """Demonstrate operations with prompt files."""
  print("\n" + "-" * 70)
  print("PROMPT FILE OPERATIONS")
  print("-" * 70)
  
  # Create prompt files from sample data
  print("\n1. Creating prompt files")
  prompt_files = []
  for sample in SAMPLE_PROMPTS:
    prompt = Prompt.create_prompt(
      base_directory=base_dir,
      prompt_name=sample["name"],
      prompt_text=sample["prompt"]
    )
    if prompt:
      prompt_files.append(prompt)
      print(f"   - Created prompt: {prompt.prompt_name} (ID: {prompt.file_id})")
  
  # Demonstrate name validation
  print("\n2. Prompt name validation")
  special_prompt = Prompt.create_prompt(
    base_directory=base_dir,
    prompt_name="Special PROMPT with Spaces & Symbols!",
    prompt_text="This prompt had a complex name that was normalized."
  )
  print(f"   - Original name: 'Special PROMPT with Spaces & Symbols!'")
  print(f"   - Normalized name: '{special_prompt.prompt_name}'")
  print(f"   - File name: '{special_prompt.file_name}'")
  
  # Load a prompt by name
  print("\n3. Loading a prompt by name")
  loaded_prompt = Prompt.load_prompt("customer-service", base_dir)
  if loaded_prompt:
    print(f"   - Loaded prompt: {loaded_prompt.prompt_name}")
    print(f"   - Prompt text: '{loaded_prompt.prompt_text}'")
  
  # Modify a prompt
  print("\n4. Modifying a prompt")
  if prompt_files:
    first_prompt = prompt_files[0]
    print(f"   - Original prompt text: '{first_prompt.prompt_text}'")
    
    # Update the prompt text
    first_prompt.prompt_text += " I work as a {{profession}}."
    first_prompt.save()
    
    # Reload to verify changes
    updated_prompt = Prompt.load(first_prompt.file_id, base_dir)
    print(f"   - Updated prompt text: '{updated_prompt.prompt_text}'")
    
    # Test that the same object also has the updated data
    print(f"   - Original object's prompt text: '{first_prompt.prompt_text}'")
    # Load by name to test that lookup
    by_name_prompt = Prompt.load_prompt("simple-greeting", base_dir)
    if by_name_prompt:
      print(f"   - Loaded by name prompt text: '{by_name_prompt.prompt_text}'")
  
  # Show all prompts in the manifest
  print("\n5. Listing all prompts in manifest")
  
  # Use BaseFile's find_files_by_criteria method to get all prompts
  prompt_metadata = Prompt.find_files_by_criteria(
    base_directory=base_dir,
    subdirectory="prompts"
  )
  
  print(f"   {'Name':<30} {'ID':<36} {'Preview'}")
  print(f"   {'-'*30} {'-'*36} {'-'*40}")
  
  for file_id, metadata in prompt_metadata.items():
    name = metadata.get("metadata", {}).get("prompt_name", "")
    if not name:
      name = metadata.get("file_name", "").replace(".json", "")
    
    # Get a preview of the prompt text
    preview = ""
    if "metadata" in metadata and "prompt_text_preview" in metadata["metadata"]:
      preview = metadata["metadata"]["prompt_text_preview"]
    
    print(f"   {name:<30} {file_id:<36} {preview if preview else 'No preview available'}")
  
  print(f"\n   Total prompts: {len(prompt_metadata)}")
  
  # Export a prompt
  print("\n6. Exporting a prompt to a file")
  if prompt_files:
    export_path = os.path.join(base_dir, "exported_prompt.json")
    result = prompt_files[0].export(export_path)
    
    if result:
      print(f"   - Exported to: {export_path}")
      
      # Verify the exported content
      with open(export_path, 'r') as f:
        data = json.load(f)
        print(f"   - Exported prompt name: {data.get('name')}")
        print(f"   - Exported prompt text: '{data.get('prompt')}'")
  
  # Get text file statistics (inherited from TextFile)
  print("\n7. Using inherited TextFile functionality")
  if prompt_files:
    stats = prompt_files[0].get_stats()
    print(f"   - Line count: {stats['line_count']}")
    print(f"   - Word count: {stats['word_count']}")
    print(f"   - Character count: {stats['char_count']}")
    
    # Search for placeholders
    search_results = prompt_files[0].search("{{.*?}}")
    print(f"   - Found {len(search_results)} placeholders:")
    for i, (line_num, line_content) in enumerate(search_results, 1):
      print(f"     {i}. {line_content}")
  
  return prompt_files



########################################################################
#                               MAIN                                   #
########################################################################
def main():
  """Run the demo."""
  # Set up the demo
  base_dir = setup_demo()
  
  try:
    # Demonstrate prompt file operations
    prompt_files = demo_prompt_files(base_dir)
    
    print("\nDemo processes completed successfully!")
  
  except Exception as e:
    print(f"Error during demo: {e}")
    import traceback
    traceback.print_exc()
  
  finally:
    # Clean up the demo directory
    print("\nCleaning up demo environment...")
    if os.path.exists(base_dir):
      shutil.rmtree(base_dir)
    print("Demo complete!")


if __name__ == "__main__":
  main() 