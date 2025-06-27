#!/usr/bin/env python3
"""
Test script for verifying the new module loading mechanism.

This script tests loading modules based on command.py files in the modules directory.
"""

import os
import sys
import logging
from typing import List, Dict, Any

# Add parent directory to path to import from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Set up logging - use DEBUG level for more details
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger()

# Handle import issues with relative vs absolute imports
# This makes both 'src.commands' and 'commands' resolve to the same path
src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if src_dir not in sys.path:
  sys.path.insert(0, src_dir)

# Import required modules - after path setup
from commands import Registry
from settings import Settings
from mod import initialize_module_system, MODULE_COMMAND_FILENAME



########################################################################
#                              FUNCTIONS                               #
########################################################################
def list_available_modules(registry: Registry, modules_dir: str) -> List[Dict[str, Any]]:
  """
  List all available modules in the modules directory.

  Args:
    registry: The command registry to check loaded modules against
    modules_dir: Path to the modules directory, relative to application root

  Returns:
    List of dictionaries containing module information
  """
  modules_info = []

  # Check if modules directory exists
  if not os.path.isdir(modules_dir):
    logger.warning(f"Modules directory '{modules_dir}' does not exist")
    return modules_info

  # Look for module directories with command.py files
  for module_name in os.listdir(modules_dir):
    # Skip hidden files and directories
    if module_name.startswith('_') or module_name.startswith('.'):
      continue

    # Get module directory
    module_path = os.path.join(modules_dir, module_name)
    if not os.path.isdir(module_path):
      continue

    # Check for command.py file
    command_file = os.path.join(module_path, MODULE_COMMAND_FILENAME)
    if not os.path.isfile(command_file):
      continue

    # Check for README.md
    readme_file = os.path.join(module_path, "README.md")

    # Check if module is loaded
    is_loaded = False
    cmd_count = 0

    if hasattr(registry, "command_modules") and module_name in registry.command_modules:
      is_loaded = True
      # Get the number of commands from this module
      if hasattr(registry, "command_map"):
        for cmd_name in registry.command_map:
          if cmd_name.startswith(f"modules_{module_name}_"):
            cmd_count += 1

    # Add module info
    modules_info.append({
      "name": module_name,
      "path": module_path,
      "has_command_py": True,
      "has_readme": os.path.isfile(readme_file),
      "is_loaded": is_loaded,
      "command_count": cmd_count
    })

  return sorted(modules_info, key=lambda x: x["name"])



########################################################################
#                              MAIN                                    #
########################################################################
def main():
  """Test the module loading mechanism."""
  logger.info("Starting module loader test")

  # Initialize the registry
  registry = Registry()

  # Create a settings object for testing
  settings = Settings()

  # Print initial command count
  logger.info(f"Registry initially contains {len(registry.command_map)} commands")

  # Get modules directory
  modules_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "modules")
  logger.info(f"Using modules directory: {modules_dir}")

  # List available modules before loading
  logger.info("Listing available modules before loading:")
  modules_before = list_available_modules(registry, modules_dir)
  for module in modules_before:
    logger.info(f"  - {module['name']} (loaded: {module['is_loaded']})")

  # Initialize module system
  initialize_module_system(registry, modules_dir)

  # Print updated command count
  logger.info(f"Registry now contains {len(registry.command_map)} commands")

  # List available modules after loading
  logger.info("Listing available modules after loading:")
  modules_after = list_available_modules(registry, modules_dir)
  for module in modules_after:
    logger.info(f"  - {module['name']} (loaded: {module['is_loaded']}, commands: {module['command_count']})")

  # Test running a module command if any were loaded
  module_commands = [cmd for cmd in registry.command_map.keys() if cmd.startswith("modules_")]
  if module_commands:
    logger.info("Found module commands:")
    for cmd in module_commands:
      logger.info(f"  - {cmd}")

    # Try executing a command
    test_cmd = module_commands[0]
    logger.info(f"Attempting to execute command: {test_cmd}")
    try:
      result = registry.execute_tool(test_cmd, {}, settings)
      logger.info(f"Command result: {result}")
    except Exception as e:
      logger.error(f"Error executing command: {str(e)}")
  else:
    logger.info("No module commands found")

  logger.info("Module loader test complete")


if __name__ == "__main__":
  main()