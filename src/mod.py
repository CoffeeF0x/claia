"""
Module loading system for CLAIA.

This module handles dynamic loading of modules (plugins) for the CLAIA application.
Modules are loaded by finding command.py files in the modules directory structure.
"""

# External dependencies
import os
import sys
import importlib
import importlib.util
import logging
import inspect
from typing import Dict, List, Any, Optional

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
            # Import the command file
            import_name = f"modules.{module_name}.command"
            logger.debug(f"Importing {import_name} from {command_file}")

            spec = importlib.util.spec_from_file_location(import_name, command_file)
            if spec is None or spec.loader is None:
                logger.error(f"Failed to load module spec for '{module_name}'")
                continue

            module = importlib.util.module_from_spec(spec)
            sys.modules[import_name] = module
            spec.loader.exec_module(module)

            # Find first class that inherits from Command
            command_class = None
            for name, obj in module.__dict__.items():
                if (inspect.isclass(obj) and
                    obj.__module__ == import_name and
                    issubclass(obj, Command) and
                    obj != Command):
                    command_class = obj
                    logger.debug(f"Found command class: {name}")
                    break

            if command_class is None:
                logger.warning(f"No Command subclass found in {command_file}")
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

    logger.info(f"Loaded {len(modules)} modules with a total of {len(registry.command_map)} commands")
    return modules


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


def initialize_module_system(registry: Registry, modules_dir: str) -> None:
    """
    Initialize the module system by loading modules.

    This should be called during application startup after the Registry is created.
    """
    logger.info("Initializing module system")
    load_modules(registry, modules_dir)
    logger.info("Module system initialized")