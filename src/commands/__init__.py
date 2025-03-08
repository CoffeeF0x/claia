# TODO:
# - refactor and simplify using argparse
#   - the cli should parse arguments as follows: GLOBAL_ARGS COMMAND COMMAND_ARGS SUBCOMMAND SUBCOMMAND_ARGS
#   - subcommand args shouldn't be available from the parent command, but parent args may be available after the subcommand
# - to simplify our setup with argparse, we'll want to add argparse values via the command decorator
# - the following values will be needed for each command:
#   - parent command (to define the tree)
#   - command name (can also be a list to define aliases)
#   - command args (not sure how to break these out)
#   - description (for function calling)
#   - help text (for argparse help)
#   - bool to enable function calling (note, function calling will be disabled if description and unique command name are not defined)
#   - parameters (for function calling, only necessary if parameters are available for the command)
# - we'll want to move the top level commands to their own file and essentially define them as a type of alias
# - build a system to convert the command name to something unique for function calling
#   - lean on the command tree structure and replace spaces with underscores
#   - to avoid confusion, especially with modules, we'll probably want to limit or prevent underscore usage for command names



# External dependencies
import importlib
import os
import sys
import logging
import types
from typing import Dict, Any, List, Tuple, Set

# Internal dependencies
from commands.prompts import PromptCommand
from commands.conversations import ConversationCommand
from commands.models import ModelCommand
from commands.system import SystemCommand
from commands.tools import ToolsCommand
from commands.massedcompute import MassedComputeCommand
from errors import Result
from settings import Settings



##################################################
#                   CONSTANTS                    #
##################################################
# Define command modules with their associated information
# Format: (command_instance, primary_names, description, is_enabled)
COMMAND_MODULES: List[Tuple[Any, List[str], str, bool]] = [
  # System commands
  (
    SystemCommand(),
    ["system", "sys", "s"],
    "technical commands such as exiting the program and clearing the screen",
    True
  ),

  # Model commands
  (
    ModelCommand(),
    ["model", "models"],
    "commands related to selecting and managing language models",
    True
  ),

  # Tools commands
  (
    ToolsCommand(),
    ["tool", "tools"],
    "utility functions such as date, time, and user information",
    True
  ),

  # Prompt commands
  (
    PromptCommand(),
    ["prompt", "prompts"],
    "commands related to prompts or system prompts",
    True
  ),

  # Conversation commands
  (
    ConversationCommand(),
    ["conversation", "conversations"],
    "commands related to conversations and saved messages",
    True
  ),

  # MassedCompute commands
  (
    MassedComputeCommand(),
    ["massedcompute", "mc"],
    "commands related to deploying and managing GPU instances",
    True
  )
]

# Logger for module loading
logger = logging.getLogger(__name__)



##################################################
#                MODULE LOADING                  #
##################################################
def load_modules() -> None:
  """
  Load all available modules from the modules directory.
  Each module must have a ModuleCommands class that extends Command.

  This function handles namespace collisions by creating uniquely named instances
  at load time rather than requiring unique class names in the modules.
  """
  try:
    # Get the modules directory path
    # Assuming the modules directory is at the same level as src
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    modules_dir = os.path.join(base_dir, "modules")

    # Check if modules directory exists
    if not os.path.isdir(modules_dir):
      logger.warning(f"Modules directory not found at {modules_dir}")
      return

    # Add modules directory to Python path if not already there
    if modules_dir not in sys.path:
      sys.path.append(modules_dir)

    # Iterate through module directories
    for module_name in os.listdir(modules_dir):
      module_path = os.path.join(modules_dir, module_name)

      # Skip non-directories and special directories
      if not os.path.isdir(module_path) or module_name.startswith('__'):
        continue

      # Check if module.py exists in the directory
      module_file = os.path.join(module_path, "module.py")
      if not os.path.isfile(module_file):
        logger.warning(f"No module.py found in {module_path}")
        continue

      try:
        # Import the module
        module_import_path = f"{module_name}.module"
        module = importlib.import_module(module_import_path)

        # Check specifically for ModuleCommands class
        if hasattr(module, "ModuleCommands"):
          command_class = module.ModuleCommands

          # Verify it's a subclass of Command
          is_command_subclass = False
          for base in command_class.__mro__:
            if base.__name__ == 'Command' and base.__module__ == 'commands.base':
              is_command_subclass = True
              break

          if not is_command_subclass:
            logger.warning(f"ModuleCommands in {module_import_path} is not a subclass of Command")
            continue

          # Create an instance of the ModuleCommands class
          module_command = command_class()

          # Set a unique name for the instance to avoid namespace collisions
          # This doesn't change the class name, just adds an attribute to the instance
          module_command._module_name = module_name
          module_command._module_path = module_path

          # Add to COMMAND_MODULES
          global COMMAND_MODULES
          COMMAND_MODULES.append(
            (
              module_command,
              [module_name],  # Use module name as the primary command name
              f"commands from the {module_name} module",
              True  # Enable by default
            )
          )

          logger.info(f"Successfully loaded module: {module_name}")
        else:
          logger.warning(f"No ModuleCommands class found in {module_import_path}")

      except Exception as e:
        logger.error(f"Error loading module {module_name}: {str(e)}")

  except Exception as e:
    logger.error(f"Error in load_modules: {str(e)}")



##################################################
#                   FUNCTIONS                    #
##################################################
# Remove extra spaces, verify there is a command and convert all commands to lowercase
def cleanup_commands(commands: list[str], settings: Settings) -> Result:
  result: Result = Result()

  if not commands:
    result = Result.fail("No command provided.")

  # Prune empty commands
  command_counter = len(commands)
  while command_counter != 0 and len(commands) > 1:
    command_counter -= 1
    if (not commands[command_counter]):
      commands.pop(command_counter)

  # Make all commands lowercase
  for index in range(len(commands)):
    commands[index] = commands[index].lower()

  return result

# Initialize the command registry with core commands and module commands
def initialize_command_registry() -> Dict[str, Any]:
  # Load modules first
  load_modules()

  registry = {}

  # Register all enabled command modules
  for cmd_instance, cmd_names, _, is_enabled in COMMAND_MODULES:
    if is_enabled:
      # Register primary command names
      for name in cmd_names:
        registry[name] = cmd_instance

      # Register top-level commands if available
      if hasattr(cmd_instance, 'get_top_level_commands'):
        top_level_commands = cmd_instance.get_top_level_commands()
        for cmd_name, cmd_func in top_level_commands.items():
          registry[cmd_name] = cmd_instance

  return registry

# Get all enabled command instances (avoiding duplicates)
def get_enabled_command_instances() -> List[Any]:
  """Get a list of all enabled command instances (without duplicates)"""
  return [cmd for cmd, _, _, enabled in COMMAND_MODULES if enabled]

# Get all function definitions for AI function calling
def get_function_definitions(settings: Settings = None) -> List[Dict[str, Any]]:
  """
  Get all AI-callable function definitions from registered commands.

  Args:
    settings: Optional settings object

  Returns:
    List of function definitions in JSON schema format
  """
  definitions = []

  try:
    # Process each enabled command instance once
    for cmd_instance in get_enabled_command_instances():
      if hasattr(cmd_instance, 'get_function_definitions'):
        # Make sure we're calling the method, not trying to iterate over it
        cmd_definitions = cmd_instance.get_function_definitions()
        if isinstance(cmd_definitions, list):
          definitions.extend(cmd_definitions)
        else:
          print(f"Warning: get_function_definitions for {cmd_instance.__class__.__name__} did not return a list")
  except Exception as e:
    print(f"Error getting function definitions: {str(e)}")
    # Return an empty list in case of error
    return []

  return definitions

# Execute a command by name using function calling format
def execute_command_by_name(function_name: str, parameters: Dict[str, Any], settings: Settings) -> str:
  """
  Execute a command by its function name with the given parameters.

  Args:
    function_name: The function name in format "path_to_command"
    parameters: Dictionary of parameter values
    settings: Settings object

  Returns:
    Result of the command as a string
  """
  if settings is None:
    return "Error: Settings object is required"

  try:
    # Split the function name into parts (path_component1_component2_...)
    parts = function_name.split('_')

    # Try each enabled command instance
    for cmd_instance in get_enabled_command_instances():
      if hasattr(cmd_instance, 'get_function_definitions'):
        for func_def in cmd_instance.get_function_definitions():
          if func_def["name"] == function_name:
            # Found the function, now navigate the command tree to find the handler
            current = cmd_instance.function_tree
            for part in parts[:-1]:  # All but the last part
              if part in current:
                current = current[part]
              else:
                return f"Invalid command path: {function_name}"

            # The last part should be the function
            last_part = parts[-1]
            if last_part in current and "function" in current[last_part]:
              func = current[last_part]["function"]
              try:
                # Call the function with settings and parameters
                result = func(settings, **parameters)
                # Convert Result objects to string
                if hasattr(result, 'message') and callable(getattr(result, 'message')):
                  return result.message()
                return str(result)
              except Exception as e:
                return f"Error executing command: {str(e)}"
            else:
              return f"Invalid command function: {function_name}"
  except Exception as e:
    return f"Error processing command: {str(e)}"

  return f"Unknown function: {function_name}"



##################################################
#          COMMAND REGISTRY DEFINITION           #
##################################################
command_registry = initialize_command_registry()

# Run the cleanup routine and execute the command
def run(input: str, settings: Settings) -> Result:
  commands = input.split()
  result = cleanup_commands(commands, settings)

  if result.is_error():
    display_help()
  elif commands[0] == "help":
    if len(commands) > 1:
      display_command_help(commands[1].lower())
    else:
      display_help()
    result = Result()
  elif (commands[0] in command_registry):
    result = command_registry[commands[0]].execute(commands, settings)
  else:
    result = Result.fail("Unrecognized command.")
    display_help()

  return result



##################################################
#                 HELP FUNCTIONS                 #
##################################################
# Display help for all commands
def display_help() -> None:
  print("Here is a list of available commands:")

  # Display primary command groups
  for cmd_instance, cmd_names, description, is_enabled in COMMAND_MODULES:
    if is_enabled:
      # Format the command names
      cmd_names_str = ", ".join(cmd_names)
      print(f"  {cmd_names_str}")
      print(f"    - {description}")

  print("  help [command|module]")
  print("    - display help information for all commands or a specific command/module")

  # Display top-level commands
  print("\nTop-level commands:")
  top_level_commands = set()

  for cmd_instance in get_enabled_command_instances():
    if hasattr(cmd_instance, 'get_top_level_commands'):
      for top_cmd, cmd_func in cmd_instance.get_top_level_commands().items():
        top_level_commands.add(top_cmd)
        # Also add aliases
        for alias in cmd_func._command_aliases:
          if isinstance(alias, str):
            top_level_commands.add(alias)

  if top_level_commands:
    print("  " + ", ".join(sorted(top_level_commands)))
    print("    - these commands can be used directly without a module prefix")

# Display help for a specific command or module
def display_command_help(command_name: str) -> None:
  if command_name in command_registry:
    if hasattr(command_registry[command_name], 'help'):
      command_registry[command_name].help()
    else:
      print(f"No help available for command: {command_name}")
  else:
    print(f"Unknown command: {command_name}")
    display_help()