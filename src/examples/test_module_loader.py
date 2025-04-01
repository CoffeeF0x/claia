#!/usr/bin/env python3
"""
Test script for verifying the new module loading mechanism.

This script tests loading modules based on command.py files in the modules directory.
"""

import os
import sys
import logging

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
from mod import initialize_module_system, list_available_modules


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