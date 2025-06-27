#!/usr/bin/env python3
"""
Simple test script for the sample module's commands.

This script demonstrates calling specific commands from the sample module.
"""

import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger()

# Handle import issues with relative vs absolute imports
# This makes both 'src.commands' and 'commands' resolve to the same path
src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Add the parent directory to sys.path for module imports
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import required modules
from commands import Registry
from settings import Settings
from mod import initialize_module_system


def main():
    """Test the sample module commands."""
    logger.info("Starting sample module test")

    # Initialize the registry
    registry = Registry()

    # Create a settings object for testing
    settings = Settings()

    # Get modules directory and initialize the module system
    modules_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "modules")
    logger.info(f"Loading modules from: {modules_dir}")
    initialize_module_system(registry, modules_dir)

    # Test hello command with no name
    logger.info("Testing 'hello' command with no name parameter:")
    result = registry.execute_tool("modules_sample_hello", {}, settings)
    logger.info(f"  Result: {result.message}")

    # Test hello command with a name
    logger.info("Testing 'hello' command with name parameter:")
    result = registry.execute_tool("modules_sample_hello", {"name": "User"}, settings)
    logger.info(f"  Result: {result.message}")

    # Test time command with default format
    logger.info("Testing 'time' command with default format:")
    result = registry.execute_tool("modules_sample_time", {}, settings)
    logger.info(f"  Result: {result.message}")

    # Test time command with unix format
    logger.info("Testing 'time' command with unix format:")
    result = registry.execute_tool("modules_sample_time", {"format": "unix"}, settings)
    logger.info(f"  Result: {result.message}")

    # Test info command
    logger.info("Testing 'info' command:")
    result = registry.execute_tool("modules_sample_info", {}, settings)
    logger.info(f"  Result: {result.message}")

    logger.info("Sample module test complete")


if __name__ == "__main__":
    main()