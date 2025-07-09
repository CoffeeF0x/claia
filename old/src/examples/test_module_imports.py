#!/usr/bin/env python3
"""
Test direct module imports.

This script tests how we can directly import module files without using the modules namespace.
"""

import os
import sys
import logging
import importlib

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger()

# Add src directory to path
src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Get the modules directory
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
modules_dir = os.path.join(base_dir, "modules")

# Add modules directory to path so modules can be loaded directly
sys.path.append(modules_dir)

def main():
    """Test importing modules directly."""
    logger.info("Starting module import test")

    try:
        # Try direct import
        logger.info("Testing direct import of modules")

        # This approach allows us to import the module directly
        # The module directory name is treated as a package
        import zammad
        logger.info(f"Successfully imported zammad module")

        # Try importing specific modules
        from zammad import constants, api, settings
        logger.info("Successfully imported zammad sub-modules")

        # Test creating a settings instance
        zammad_settings = settings.ZammadSettings()
        logger.info(f"Created ZammadSettings instance")

        # Print constants
        logger.info(f"ENV_ZAMMAD_API_TOKEN: {constants.ENV_ZAMMAD_API_TOKEN}")
        logger.info(f"Available tags: {len(constants.TAG_LIST)} tags")

        # Success!
        logger.info("All imports successful!")
    except Exception as e:
        logger.error(f"Error importing modules: {e}")

    logger.info("Module import test complete")


if __name__ == "__main__":
    main()