"""
Module loading system for CLAIA.

This module handles dynamic loading of modules (plugins) for the CLAIA application.
Modules are loaded from the modules directory and must follow a specific structure.
"""

# External dependencies
import os
import sys
import importlib
import importlib.util
import logging
from typing import Dict, List, Any, Optional, Type
from pathlib import Path

# Internal dependencies
from commands import Registry



########################################################################
#                              CONSTANTS                               #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                            MODULE LOADING                            #
########################################################################
def load_modules(registry: Registry, modules_dir: str) -> Dict[str, Any]:
    """
    Load all available modules from the modules directory.

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

    # Look for module directories
    for item in os.listdir(modules_dir):
        module_path = os.path.join(modules_dir, item)

        # Skip if not a directory or starts with underscore (hidden/disabled)
        if not os.path.isdir(module_path) or item.startswith("_"):
            continue

        module_file = os.path.join(module_path, "module.py")

        # Skip if module.py doesn't exist
        if not os.path.isfile(module_file):
            logger.warning(f"Skipping '{item}': missing module.py file")
            continue

        try:
            # Import the module
            module_name = f"modules.{item}.module"
            spec = importlib.util.spec_from_file_location(module_name, module_file)
            if spec is None or spec.loader is None:
                logger.error(f"Failed to load module spec for '{item}'")
                continue

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Check if module has ModuleCommands class
            if not hasattr(module, "ModuleCommands"):
                logger.warning(f"Skipping '{item}': missing ModuleCommands class")
                continue

            # Create instance of ModuleCommands
            module_instance = module.ModuleCommands()

            # Set module name in the instance
            module_instance._module_name = item
            module_instance._module_path = module_path

            # Add to modules dict
            modules[item] = module_instance

            # Register the module with the registry
            registry.add_command_module(
                module_instance,
                [item],  # Primary name is the directory name
                f"Module commands for {item}",
                True     # Enabled by default
            )

            logger.info(f"Loaded module: {item}")
        except Exception as e:
            logger.error(f"Error loading module '{item}': {str(e)}")

    logger.info(f"Loaded {len(modules)} modules")
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

    # Look for module directories
    for item in os.listdir(modules_dir):
        module_path = os.path.join(modules_dir, item)

        # Skip if not a directory or starts with underscore (hidden/disabled)
        if not os.path.isdir(module_path) or item.startswith("_"):
            continue

        module_file = os.path.join(module_path, "module.py")
        readme_file = os.path.join(module_path, "README.md")

        # Check if module is loaded
        is_loaded = False
        if hasattr(registry, "command_modules"):
            for cmd in registry.get_enabled_command_instances():
                if hasattr(cmd, "_module_name") and cmd._module_name == item:
                    is_loaded = True
                    break

        # Add module info
        modules_info.append({
            "name": item,
            "path": module_path,
            "has_module_py": os.path.isfile(module_file),
            "has_readme": os.path.isfile(readme_file),
            "is_loaded": is_loaded
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