#!/usr/bin/env python3
"""
Test the simple module commands.

This demonstrates our simplified module loading system.
"""

import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger()

# Add paths for imports
src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Import required modules
from commands import Registry
from settings import Settings
from mod import load_modules


def main():
    """Test the simple module."""
    logger.info("Starting simple module test")

    # Initialize registry and settings
    registry = Registry()
    settings = Settings()

    # Get modules directory
    modules_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "modules")

    # Load modules (directly using load_modules to show how simple it is)
    loaded_modules = load_modules(registry, modules_dir)

    # Check if simple module was loaded
    if "simple" in loaded_modules:
        logger.info("Simple module was loaded successfully!")

        # Test the hello command
        logger.info("Testing 'hello' command:")
        result = registry.execute_tool("modules_simple_hello", {}, settings)
        logger.info(f"  Result: {result.message}")

        # Test the echo command
        logger.info("Testing 'echo' command:")
        result = registry.execute_tool("modules_simple_echo", {"message": "Hello, World!"}, settings)
        logger.info(f"  Result: {result.message}")
    else:
        logger.error("Simple module was not loaded")

    logger.info("Simple module test complete")


if __name__ == "__main__":
    main()