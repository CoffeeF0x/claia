#!/usr/bin/env python3
"""
Demo selector for the commands module classes.
Allows user to select and test different command functionality.
"""

# External dependencies
import logging
import uuid
import os

# Internal dependencies
from ._demo import (
  MockCommand1Demo,
  MockCommand2Demo
)


########################################################################
#                             CONSTANTS                                #
########################################################################
# Directory structure constants
DEFAULT_STORAGE_DIR = "storage"
DEMOS_SUBDIR = "demos"

# Available demos
DEMOS = [
  "Mock Command 1 Demo",
  "Mock Command 2 Demo"
]


########################################################################
#                             FUNCTIONS                                #
########################################################################
def display_menu() -> None:
  """Display the available demos menu."""
  print("\n" + "="*50)
  print("     CLAIA Commands Module Demo Selector")
  print("="*50)
  print("Available demos:")
  print()

  for i, demo in enumerate(DEMOS, 1):
    print(f"  {i}. {demo}")

  print(f"  {len(DEMOS) + 1}. Exit")
  print("="*50)


def get_user_selection() -> str:
  """Get the user's demo selection."""
  while True:
    try:
      choice = input(f"\nSelect a demo (1-{len(DEMOS) + 1}): ").strip()

      if not choice:
        continue

      choice_num = int(choice)

      if choice_num == len(DEMOS) + 1:
        return ""  # Exit signal

      if 1 <= choice_num <= len(DEMOS):
        return DEMOS[choice_num - 1]
      else:
        print(f"Please enter a number between 1 and {len(DEMOS) + 1}")

    except ValueError:
      print("Please enter a valid number")
    except KeyboardInterrupt:
      print("\nGoodbye!")
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
    "Mock Command 1 Demo": MockCommand1Demo(session_dir).run,
    "Mock Command 2 Demo": MockCommand2Demo(session_dir).run
  }

  if selected_demo in demo_map:
    demo_map[selected_demo]()
  else:
    print(f"Demo not implemented: {selected_demo}")

  print("-" * 50)


def main() -> None:
  """Main function to run the demo selector."""
  print("Welcome to the CLAIA Commands Module Demo!")
  print("This demonstrates mock functionality for the commands module classes.")

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
