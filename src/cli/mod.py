"""
This module provides support for loading external modules in CLAIA.

Modules are loaded by finding specific files in the modules directory structure.
These modules can provide additional commands, tools, and other functionality.
"""

# External dependencies
import os
import sys
import importlib.util
import logging
import inspect
from typing import Dict, Any

# Internal dependencies
from commands import CommandRegistry, Command
from agents import Agent



########################################################################
#                              CONSTANTS                               #
########################################################################
logger = logging.getLogger(__name__)
MODULE_COMMAND_FILENAME = "command.py"
AGENT_COMMAND_FILENAME = "agent.py"
MODEL_COMMAND_FILENAME = "model.py"



########################################################################
#                            MODULE LOADING                            #
########################################################################
def load_modules(registry: CommandRegistry, modules_dir: str) -> Dict[str, Any]:
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

  # Add modules directory to Python path if not already there
  if modules_dir not in sys.path:
    sys.path.insert(0, modules_dir)
    logger.debug(f"Added modules directory to Python path: {modules_dir}")

  # Look for module directories
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
    has_command = os.path.isfile(command_file)

    # Check for agent.py file
    agent_file = os.path.join(module_path, AGENT_COMMAND_FILENAME)
    has_agent = os.path.isfile(agent_file)

    # If neither file exists, skip this directory
    if not has_command and not has_agent:
      continue

    # Import the module if it has either file
    try:
      # Load command module if it exists
      if has_command:
        module_instance = load_command_module(module_name, module_path, registry)
        if module_instance:
          modules[module_name] = module_instance

      # Load agent module if it exists
      if has_agent:
        load_agent_module(module_name, module_path)

    except Exception as e:
      logger.error(f"Error loading module '{module_name}': {str(e)}")

  logger.info(f"Loaded {len(modules)} modules for a total of {len(registry.command_map)} commands")
  return modules


def load_command_module(module_name: str, module_path: str, registry: CommandRegistry) -> Any:
  """
  Load a command module and register it with the command registry.

  Args:
      module_name: The name of the module
      module_path: The path to the module directory
      registry: The command registry to register the module with

  Returns:
      The command module instance if successful, None otherwise
  """
  try:
    logger.debug(f"Importing command module {module_name}")

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
      return None

    # Create instance of the Command class
    module_instance = command_class()

    # Set module name in the instance
    module_instance._module_name = module_name
    module_instance._module_path = module_path

    # Register the module with the registry
    registry.add_command_module(
      module_instance,
      [module_name],  # Primary name is the directory name
      f"Module commands for {module_name}",
      True   # Enabled by default
    )

    # Log success with number of commands
    command_count = len(module_instance.command_map) if hasattr(module_instance, 'command_map') else 0
    logger.info(f"Loaded command module: {module_name} with {command_count} commands")

    return module_instance

  except Exception as e:
    logger.error(f"Error loading command module '{module_name}': {str(e)}")
    return None


def load_agent_module(module_name: str, module_path: str) -> None:
  """
  Load an agent module and register it with the Agent system.

  Args:
      module_name: The name of the module
      module_path: The path to the module directory
  """
  try:
    logger.debug(f"Importing agent module {module_name}")

    # Check if __init__.py exists to ensure it's a proper package
    init_file = os.path.join(module_path, "__init__.py")
    if not os.path.isfile(init_file):
      logger.warning(f"Agent module {module_name} missing __init__.py file, may cause import issues")

    # Import the main module
    module = importlib.import_module(module_name)

    # Now import the agent module
    agent_module_name = f"{module_name}.agent"
    agent_module = importlib.import_module(agent_module_name)

    # Find agent class (first class that inherits from BaseAgent)
    agent_class = None
    for name, obj in agent_module.__dict__.items():
      if (inspect.isclass(obj) and
        obj.__module__ == agent_module_name and
        'BaseAgent' in [base.__name__ for base in obj.__mro__ if base.__name__ != obj.__name__]):
        agent_class = obj
        logger.debug(f"Found agent class: {name}")
        break

    if agent_class is None:
      logger.warning(f"No BaseAgent subclass found in {agent_module_name}")
      return

    # Register the agent with the global Agent registry
    # Use the module name as the agent type (lowercase)
    agent_type = module_name.lower()
    Agent.register_agent(agent_type, agent_class)
    logger.info(f"Registered agent {agent_class.__name__} for type {agent_type}")

  except Exception as e:
    logger.error(f"Error loading agent module '{module_name}': {str(e)}")


def initialize_module_system(registry: CommandRegistry, modules_dir: str) -> None:
  """
  Initialize the module system by loading modules.

  This should be called during application startup after the Registry is created.
  """
  logger.info("Initializing module system")
  load_modules(registry, modules_dir)
  logger.info("Module system initialized")