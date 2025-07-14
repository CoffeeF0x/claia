#!/usr/bin/env python3
"""
Main entry point for the new src directory modules.
Allows user to select and run different modules.
"""

# External dependencies
from pathlib import Path
import importlib.util
import logging
import sys



########################################################################
#                              CONSTANTS                               #
########################################################################
MODULES = [
  "agents",
  "cli",
  "commands",
  "common",
  "models",
  "modules",
  "tests"
]



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = None



########################################################################
#                              FUNCTIONS                               #
########################################################################
def setup_logger() -> logging.Logger:
  """
  Setup and configure logger for the application.

  Returns:
    Configured logger instance
  """
  # Create logs directory if it doesn't exist
  log_dir = Path("logs")
  log_dir.mkdir(exist_ok=True)

  # Create logger
  logger = logging.getLogger("claia_main")
  logger.setLevel(logging.INFO)

  # Create formatters
  file_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  )
  console_formatter = logging.Formatter(
    '%(levelname)s - %(message)s'
  )

  # File handler
  file_handler = logging.FileHandler(log_dir / "main.log")
  file_handler.setLevel(logging.INFO)
  file_handler.setFormatter(file_formatter)

  # Console handler
  console_handler = logging.StreamHandler(sys.stdout)
  console_handler.setLevel(logging.WARNING)
  console_handler.setFormatter(console_formatter)

  # Add handlers to logger (only if not already added)
  if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

  return logger


def handle_module_selection(selected_module: str) -> None:
  """
  Handle the selected module by importing and running its __main__.py.

  Args:
    selected_module: The name of the selected module
  """
  logger.info(f"Starting module: {selected_module}")
  print(f"Running module: {selected_module}")
  print("-" * 30)

  try:
    # Get the path to the module's __main__.py file
    module_main_path = f"src/{selected_module}/__main__.py"
    logger.debug(f"Loading module from path: {module_main_path}")

    # Load and execute the __main__.py file
    spec = importlib.util.spec_from_file_location("__main__", module_main_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    logger.info(f"Successfully executed module: {selected_module}")

  except Exception as e:
    logger.error(f"Error running module {selected_module}: {e}")
    print(f"Error running module {selected_module}: {e}")

  print("-" * 30)


def display_menu() -> None:
  """Display the available modules menu."""
  print("\n" + "="*50)
  print("Available Modules:")
  print("="*50)

  for i, module in enumerate(MODULES, 1):
    print(f"{i}. {module}")

  print("0. Exit")
  print("="*50)


def get_user_selection() -> str:
  """
  Get user selection from the menu.

  Returns:
    The selected module name, or empty string to exit
  """
  while True:
    try:
      choice = input("\nEnter your choice (0-{}): ".format(len(MODULES)))

      if choice == "0":
        return ""

      choice_num = int(choice)
      if 1 <= choice_num <= len(MODULES):
        return MODULES[choice_num - 1]
      else:
        print(f"Invalid choice. Please enter a number between 0 and {len(MODULES)}.")

    except ValueError:
      print("Invalid input. Please enter a number.")
    except KeyboardInterrupt:
      print("\nExiting...")
      return ""


def main() -> None:
  """Main function to run the module selector."""
  global logger
  logger = setup_logger()

  logger.info("CLAIA Module Selector started")
  print("Welcome to the CLAIA Module Selector!")

  while True:
    display_menu()
    selected_module = get_user_selection()

    if not selected_module:
      logger.info("User requested exit")
      print("Goodbye!")
      break

    handle_module_selection(selected_module)

  logger.info("CLAIA Module Selector ended")


if __name__ == "__main__":
  main()
