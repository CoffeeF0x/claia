"""
Demo selector for the models module classes.
Allows user to select and test different model functionality.
"""

# External dependencies
import logging
import uuid
import os
import sys
from datetime import datetime

# Internal dependencies
from models.config import ModelConfig
from models.demo import (
  GemmaTextDemo,
  GemmaSpecializedDemo,
  OpenAIAPIDemo
)


########################################################################
#                             CONSTANTS                                #
########################################################################
# Directory structure constants
DEFAULT_STORAGE_DIR = "storage"
DEMOS_SUBDIR = "demos"

# Available demos
DEMOS = [
  "Gemma-3-1B-IT Text Demo",
  "Gemma-3-4B-IT Specialized Demo",
  "OpenAI API Models Demo"
]


########################################################################
#                             FUNCTIONS                                #
########################################################################
def display_menu() -> None:
  """Display the available demos menu."""
  print("\n" + "="*50)
  print("     CLAIA Models Module Demo Selector")
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


def handle_demo_selection(selected_demo: str, session_dir: str, config) -> None:
  """
  Handle the selected demo by running the appropriate demonstration.

  Args:
  selected_demo: The name of the selected demo
  session_dir: The session directory for demo files
  config: Model configuration
  """
  print(f"\nRunning demo: {selected_demo}")
  print("-" * 50)

  # Create demo instances and map
  demo_map = {
    "Gemma-3-1B-IT Text Demo": lambda: GemmaTextDemo(session_dir, config).run(),
    "Gemma-3-4B-IT Specialized Demo": lambda: GemmaSpecializedDemo(session_dir, config).run(),
    "OpenAI API Models Demo": lambda: OpenAIAPIDemo(session_dir, config).run()
  }

  if selected_demo in demo_map:
    try:
      demo_map[selected_demo]()
      print(f"\n✅ {selected_demo} completed successfully!")
    except Exception as e:
      print(f"\n❌ {selected_demo} failed: {str(e)}")
      logger.error(f"Demo {selected_demo} failed: {str(e)}")
  else:
    print(f"\n❌ Demo '{selected_demo}' not found.")

  print("-" * 50)


def main() -> None:
  """Main entry point for models package demo."""
  print("\n🚀 CLAIA Models Package Demo")
  print("=" * 50)
  
  # Create session directory
  session_dir = os.path.join(os.getcwd(), "demo_sessions", f"models_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
  os.makedirs(session_dir, exist_ok=True)
  
  # Initialize model configuration
  config = ModelConfig(models_directory=os.path.join(session_dir, 'models'))
  logger = logging.getLogger(__name__)
  print(f"Demo session directory: {session_dir}")
  logger.info(f"Demo session initialized")

  while True:
    display_menu()
    selected_demo = get_user_selection()

    if selected_demo:
      handle_demo_selection(selected_demo, session_dir, config)
    else:
      print("\n👋 Goodbye!")
      break


if __name__ == "__main__":
  main()
