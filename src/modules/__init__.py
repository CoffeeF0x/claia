"""
Module loader system for Claia
"""

import os
import importlib
import importlib.util
import sys
from typing import Dict, List, Any, Optional, Callable
import inspect



##################################################
#                   CONSTANTS                    #
##################################################
# Define the module directories to search
MODULE_DIRS = [
  os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "modules")
]

# Add user module directory if specified in environment
if "CLAIA_MODULE_PATH" in os.environ:
  MODULE_DIRS.extend(os.environ["CLAIA_MODULE_PATH"].split(os.pathsep))



##################################################
#                   FUNCTIONS                    #
##################################################
def discover_modules() -> Dict[str, Any]:
  """
  Discover all available modules in the module directories.

  Returns:
    Dict[str, Any]: Dictionary of module names to module objects
  """
  modules = {}

  for module_dir in MODULE_DIRS:
    if not os.path.exists(module_dir):
      continue

    for item in os.listdir(module_dir):
      module_path = os.path.join(module_dir, item)

      # Check if it's a directory with an __init__.py file
      if os.path.isdir(module_path) and os.path.exists(os.path.join(module_path, "__init__.py")):
        module_name = item

        try:
          # Import the module
          spec = importlib.util.spec_from_file_location(
            f"modules.{module_name}",
            os.path.join(module_path, "__init__.py")
          )
          if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"modules.{module_name}"] = module
            spec.loader.exec_module(module)
            modules[module_name] = module
        except Exception as e:
          print(f"Error loading module {module_name}: {e}")

  return modules

def get_module_commands() -> Dict[str, Any]:
  """
  Get all command classes from loaded modules.

  Returns:
    Dict[str, Any]: Dictionary of command names to command classes
  """
  commands = {}
  modules = discover_modules()

  for module_name, module in modules.items():
    # Check if the module has a commands.py file
    try:
      commands_module = importlib.import_module(f"modules.{module_name}.commands")

      # Look for command classes
      for attr_name in dir(commands_module):
        attr = getattr(commands_module, attr_name)

        # Check if it's a class that ends with "Command"
        if isinstance(attr, type) and attr_name.endswith("Command"):
          command_name = module_name.lower()
          try:
            # Use inspect.isabstract to check if the class is abstract
            if not inspect.isabstract(attr):
              commands[command_name] = attr()
          except Exception as e:
            print(f"Error instantiating command {attr_name} from module {module_name}: {e}")
    except ImportError:
      # Module doesn't have commands.py, that's okay
      pass

  print(f"Loaded commands: {list(commands.keys())}")
  print(f"Command values: {list(commands.values())}")
  return commands

def get_module_functions(settings=None) -> Dict[str, Callable]:
  """
  Get all functions from loaded modules that are enabled in settings.

  Args:
    settings: Optional settings object to check if modules are enabled

  Returns:
    Dict[str, Callable]: Dictionary of function names to function objects
  """
  functions = {}
  modules = discover_modules()

  for module_name, module in modules.items():
    # Skip if module is disabled in settings
    if settings and hasattr(settings, "disabled_modules") and module_name in settings.disabled_modules:
      continue

    # Check if the module has a functions.py file
    try:
      functions_module = importlib.import_module(f"modules.{module_name}.functions")

      # Look for functions
      for attr_name in dir(functions_module):
        attr = getattr(functions_module, attr_name)

        # Skip private attributes and non-functions
        if attr_name.startswith("_") or not callable(attr):
          continue

        # Add the function with a prefix to avoid name collisions
        function_name = f"{module_name}_{attr_name}"
        functions[function_name] = attr
    except ImportError:
      # Module doesn't have functions.py, that's okay
      pass

  return functions

def get_function_definitions() -> List[Dict[str, Any]]:
  """
  Get function definitions for all module functions.

  Returns:
    List[Dict[str, Any]]: List of function definitions
  """
  definitions = []
  modules = discover_modules()

  for module_name, module in modules.items():
    # Check if the module has a functions.py file
    try:
      functions_module = importlib.import_module(f"modules.{module_name}.functions")

      # Check if the module has a FUNCTION_DEFINITIONS attribute
      if hasattr(functions_module, "FUNCTION_DEFINITIONS"):
        module_definitions = getattr(functions_module, "FUNCTION_DEFINITIONS")

        # Add module name prefix to function names
        for definition in module_definitions:
          if "name" in definition:
            definition["name"] = f"{module_name}_{definition['name']}"

        definitions.extend(module_definitions)
    except ImportError:
      # Module doesn't have functions.py, that's okay
      pass

  return definitions

# Export the functions
__all__ = [
  "discover_modules",
  "get_module_commands",
  "get_module_functions",
  "get_function_definitions"
]