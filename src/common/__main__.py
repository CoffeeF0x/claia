"""
Demo selector for the common module classes.
Allows user to select and test different common functionality.
"""

# External dependencies
import logging
import uuid
import os

# Internal dependencies
from common._demo import (
  BaseFileDemo,
  TextFileDemo,
  PromptDemo,
  ConversationDemo,
  ResultDemo,
  FileManifestDemo
)


########################################################################
#                             CONSTANTS                                #
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


########################################################################
#                             FUNCTIONS                                #
########################################################################
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


def handle_demo_selection(selected_demo: str, session_dir: str) -> None:
  """
  Handle the selected demo by running the appropriate demonstration.

  Args:
  selected_demo: The name of the selected demo
  session_dir: The session directory for demo files
  """
  print(f"\nRunning demo: {selected_demo}")
  print("-" * 50)

  # Create demo instances and map
  demo_map = {
    "BaseFile Demo":     BaseFileDemo(session_dir).run,
    "TextFile Demo":     TextFileDemo(session_dir).run,
    "Prompt Demo":       PromptDemo(session_dir).run,
    "Conversation Demo": ConversationDemo(session_dir).run,
    "Result Demo":       ResultDemo(session_dir).run,
    "FileManifest Demo": FileManifestDemo(session_dir).run
  }

  if selected_demo in demo_map:
    demo_map[selected_demo]()
  else:
    print(f"Demo not implemented: {selected_demo}")

  print("-" * 50)


def main() -> None:
  """Main function to run the demo selector."""
  print("Welcome to the CLAIA Common Module Demo!")
  print("This demonstrates the core functionality of the common module classes.")

  # Create unique demo session directory
  session_id = str(uuid.uuid4())[:8]  # Use first 8 chars of UUID

  # Build directory structure: storage/demos/{session_id}/
  base_dir = os.path.abspath(DEFAULT_STORAGE_DIR)
  demos_dir = os.path.join(base_dir, DEMOS_SUBDIR)
  session_dir = os.path.join(demos_dir, session_id)

  # Create directories if they don't exist
  os.makedirs(session_dir, exist_ok=True)

  # Initialize logging
  logger = logging.getLogger(__name__)
  print(f"Demo session directory: {session_dir}")
  logger.info(f"Demo session initialized: {session_id}")

  while True:
    display_menu()
    selected_demo = get_user_selection()

    if not selected_demo:
      print("Goodbye!")
      break

    handle_demo_selection(selected_demo, session_dir)


if __name__ == "__main__":
  main()
