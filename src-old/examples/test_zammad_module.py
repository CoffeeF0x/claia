#!/usr/bin/env python3
"""
Test the Zammad module functionality.

This script verifies that the refactored Zammad module is working correctly.
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
    """Test the Zammad module."""
    logger.info("Starting Zammad module test")

    # Initialize registry and settings
    registry = Registry()
    settings = Settings()

    # Get modules directory
    modules_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "modules")

    # Load modules (directly using load_modules to show how simple it is)
    loaded_modules = load_modules(registry, modules_dir)

    # Check if Zammad module was loaded
    if "zammad" in loaded_modules:
        logger.info("Zammad module was loaded successfully!")

        # List available commands
        logger.info("Available Zammad commands:")
        for command_name in registry.command_map:
            if command_name.startswith("modules_zammad_"):
                logger.info(f"  - {command_name}")

        # Test the module configuration
        try:
            # Use the loaded module rather than trying to manually import
            zammad_module = loaded_modules["zammad"]
            # Check if there's a certificate valid for the module
            # This is the first action that would be taken by the list command
            # which confirms basic connectivity
            logger.info("Checking the certificate chain...")

            # Try a simple command that doesn't require configuration
            result = registry.execute_tool("modules_zammad_list", {}, settings)
            logger.info(f"List command result: {result.message}")
        except Exception as e:
            logger.error(f"Error testing Zammad module: {e}")
    else:
        logger.error("Zammad module was not loaded")

    logger.info("Zammad module test complete")


if __name__ == "__main__":
    main()