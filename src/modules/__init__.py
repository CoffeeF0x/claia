"""
This module handles loading and managing external modules for the CLAI application.

It provides functionality to load command and function modules from the specified
modules directory in the settings.
"""

# External dependencies
import os
import importlib.util
import logging
from typing import List, Dict, Any, Optional, Tuple

# Internal dependencies
from commands.base import Command
from errors import Result


########################################################################
#                               CONSTANTS                              #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                              FUNCTIONS                               #
########################################################################
def load(settings) -> None:
    """
    Load all modules from the modules directory.

    Args:
        settings: Application settings
    """
    # Get modules directory from root of project, not from src
    modules_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    modules_dir = os.path.join(modules_dir, "..", settings.modules_directory)
    modules_dir = os.path.abspath(modules_dir)  # Resolve the relative path

    # Ensure the modules directory exists
    if not os.path.exists(modules_dir):
        logger.error(f"Modules directory not found: {modules_dir}")
        return

    # Initialize module lists if they don't exist
    if not hasattr(settings, "command_modules"):
        settings.command_modules = []
    if not hasattr(settings, "function_modules"):
        settings.function_modules = []

    # Scan each module directory
    for item in os.listdir(modules_dir):
        module_path = os.path.join(modules_dir, item)

        # Skip if not a directory
        if not os.path.isdir(module_path):
            continue

        # Look for module.py file
        module_file = os.path.join(module_path, "module.py")
        if not os.path.exists(module_file):
            logger.warning(f"No module.py found in {item}, skipping")
            continue

        try:
            # Check if the module has commands or functions without fully loading it
            has_commands = False
            has_functions = False

            # Load the module to check its contents
            spec = importlib.util.spec_from_file_location(f"modules.{item}", module_file)
            if spec is None or spec.loader is None:
                logger.error(f"Failed to load module spec for {item}")
                continue

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Check for ModuleCommands class
            if hasattr(module, "ModuleCommands"):
                has_commands = True
                if item not in settings.command_modules:
                    settings.command_modules.append(item)
                    logger.info(f"Registered command module: {item}")

            # Check for functions
            if hasattr(module, "FUNCTION_DEFINITIONS"):
                has_functions = True
                if item not in settings.function_modules:
                    settings.function_modules.append(item)
                    logger.info(f"Registered function module: {item}")

            if has_commands or has_functions:
                logger.info(f"Successfully registered module: {item}")
            else:
                logger.warning(f"Module {item} has no commands or functions")

        except Exception as e:
            logger.error(f"Error scanning module {item}: {str(e)}")

def get_module_path(module_name: str) -> str:
    """
    Get the file path for a module.

    Args:
        module_name: Name of the module

    Returns:
        str: Absolute path to the module.py file
    """
    # Get the modules directory by going up to the project root
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "..", "modules", module_name, "module.py")

def get_module_commands(module_name: str) -> Optional[Command]:
    """
    Load and return a command instance from a module.

    Args:
        module_name: Name of the module to load

    Returns:
        Optional[Command]: Command instance or None if not found
    """
    try:
        # Get the module path
        module_path = get_module_path(module_name)

        if not os.path.exists(module_path):
            logger.error(f"Module file not found: {module_path}")
            return None

        # Load the module
        spec = importlib.util.spec_from_file_location(f"modules.{module_name}", module_path)
        if spec is None or spec.loader is None:
            logger.error(f"Failed to load module spec for {module_name}")
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Check for ModuleCommands class
        if hasattr(module, "ModuleCommands"):
            command_class = getattr(module, "ModuleCommands")
            command_instance = command_class()
            # Set the command name to the module name
            command_instance.name = module_name
            return command_instance

        return None
    except Exception as e:
        logger.error(f"Error loading command from module {module_name}: {str(e)}")
        return None

def get_module_functions(module_name: str) -> List[Dict[str, Any]]:
    """
    Load and return function definitions from a module.

    Args:
        module_name: Name of the module to load

    Returns:
        List[Dict[str, Any]]: List of function definitions or empty list if not found
    """
    try:
        # Get the module path
        module_path = get_module_path(module_name)

        if not os.path.exists(module_path):
            logger.error(f"Module file not found: {module_path}")
            return []

        # Load the module
        spec = importlib.util.spec_from_file_location(f"modules.{module_name}", module_path)
        if spec is None or spec.loader is None:
            logger.error(f"Failed to load module spec for {module_name}")
            return []

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Check for FUNCTION_DEFINITIONS
        if hasattr(module, "FUNCTION_DEFINITIONS"):
            return module.FUNCTION_DEFINITIONS

        return []
    except Exception as e:
        logger.error(f"Error loading functions from module {module_name}: {str(e)}")
        return []
