"""
Module loading system for CLAIA.

This module handles dynamic loading of modules (plugins) for the CLAIA application.
Modules are loaded by finding command.py files in the modules directory structure.
"""

# External dependencies
import os
import sys
import importlib.util
import logging
import inspect
from typing import Dict, Any

# Internal dependencies
from commands import Registry, Command



########################################################################
#                              CONSTANTS                               #
########################################################################
logger = logging.getLogger(__name__)
MODULE_COMMAND_FILENAME = "command.py"



########################################################################
#                            MODULE LOADING                            #
########################################################################
def load_modules(registry: Registry, modules_dir: str) -> Dict[str, Any]:
    """
    Load all available modules from the modules directory by finding command.py files.

    Args:
        registry: The command registry to register modules with
        modules_dir: Path to the modules directory, relative to application root

    Returns:
        Dictionary mapping module names to module instances
    """
    logger.info(f"Loading modules from {modules_dir}")
    modules = {}

    # Check if modules directory exists
    if not os.path.isdir(modules_dir):
        logger.warning(f"Modules directory '{modules_dir}' does not exist")
        return modules

    # Add modules directory to Python path if not already there
    if modules_dir not in sys.path:
        sys.path.insert(0, modules_dir)
        logger.debug(f"Added modules directory to Python path: {modules_dir}")

    # Only look for command.py files directly in module directories
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

        try:
            # First import the whole module
            logger.debug(f"Importing module {module_name}")

            # Check if __init__.py exists to ensure it's a proper package
            init_file = os.path.join(module_path, "__init__.py")
            if not os.path.isfile(init_file):
                logger.warning(f"Module {module_name} missing __init__.py file, may cause import issues")

            # Import the main module
            module = importlib.import_module(module_name)

            # Now import the command module
            command_module_name = f"{module_name}.command"
            command_module = importlib.import_module(command_module_name)

            # Find first class that inherits from Command
            command_class = None
            for name, obj in command_module.__dict__.items():
                if (inspect.isclass(obj) and
                    obj.__module__ == command_module_name and
                    issubclass(obj, Command) and
                    obj != Command):
                    command_class = obj
                    logger.debug(f"Found command class: {name}")
                    break

            if command_class is None:
                logger.warning(f"No Command subclass found in {command_module_name}")
                continue

            # Create instance of the Command class
            module_instance = command_class()

            # Set module name in the instance
            module_instance._module_name = module_name
            module_instance._module_path = module_path

            # Add to modules dict
            modules[module_name] = module_instance

            # Register the module with the registry
            registry.add_command_module(
                module_instance,
                [module_name],  # Primary name is the directory name
                f"Module commands for {module_name}",
                True     # Enabled by default
            )

            # Log success with number of commands
            command_count = len(module_instance.command_map) if hasattr(module_instance, 'command_map') else 0
            logger.info(f"Loaded module: {module_name} with {command_count} commands")
        except Exception as e:
            logger.error(f"Error loading module '{module_name}': {str(e)}")

    logger.info(f"Loaded {len(modules)} modules for a total of {len(registry.command_map)} commands")
    return modules


def initialize_module_system(registry: Registry, modules_dir: str) -> None:
    """
    Initialize the module system by loading modules.

    This should be called during application startup after the Registry is created.
    """
    logger.info("Initializing module system")
    load_modules(registry, modules_dir)
    logger.info("Module system initialized")