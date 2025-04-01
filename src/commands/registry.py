"""
This module provides a Registry class for managing commands in the CLAIA application.

The Registry is implemented as a singleton to ensure a single point of command registration
and access throughout the application.
"""

# External dependencies
import logging
from typing import Dict, Any, List, Tuple, Optional, Callable

# Internal dependencies
from errors import Result
from settings import Settings
from .prompts import PromptCommand
from .conversations import ConversationCommand
from .models import ModelCommand
from .system import SystemCommand
from .tools import ToolsCommand
from .massedcompute import MassedComputeCommand
from .agents import AgentCommand



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                             REGISTRY                                 #
########################################################################
class Registry:
  """
  Singleton class for registering and managing commands in the application.

  The Registry maintains a mapping of command names to their implementations,
  provides methods for command execution, and handles help functionality.
  """
  _instance = None

  # Define core command modules with their associated information
  # Format: (command_class, primary_names, description, is_enabled)
  CORE_COMMAND_MODULES: List[Tuple[Any, List[str], str, bool]] = [
    # System commands
    (
      SystemCommand,
      ["system", "sys", "s"],
      "technical commands such as exiting the program and clearing the screen",
      True
    ),

    # Model commands
    (
      ModelCommand,
      ["model", "models"],
      "commands related to selecting and managing language models",
      True
    ),

    # Tools commands
    (
      ToolsCommand,
      ["tool", "tools"],
      "utility functions such as date, time, and user information",
      True
    ),

    # Prompt commands
    (
      PromptCommand,
      ["prompt", "prompts"],
      "commands related to prompts or system prompts",
      True
    ),

    # Conversation commands
    (
      ConversationCommand,
      ["conversation", "conversations"],
      "commands related to conversations and saved messages",
      True
    ),

    # MassedCompute commands
    (
      MassedComputeCommand,
      ["massedcompute", "mc"],
      "commands related to deploying and managing GPU instances",
      True
    ),

    # Agent commands
    (
      AgentCommand,
      ["agent", "agents"],
      "commands related to agent selection and management",
      True
    )
  ]

  def __new__(cls):
    if cls._instance is None:
      cls._instance = super(Registry, cls).__new__(cls)
      cls._instance._initialized = False
    return cls._instance

  def __init__(self):
    if not self._initialized:
      logger.debug("Initializing Command Registry")
      self._command_registry = {}
      self._command_modules = {}
      self._initialized = True
      self._initialize_core_commands()

  @property
  def command_registry(self) -> Dict[str, Any]:
    """Get the command registry dictionary."""
    return self._command_registry

  @property
  def command_modules(self) -> Dict[str, Tuple[Any, List[str], str, bool]]:
    """Get the command modules dictionary."""
    return self._command_modules

  def _initialize_core_commands(self) -> None:
    """
    Initialize core command modules.

    This method creates instances of core command classes and registers them
    with the registry. It's called automatically during initialization.
    """
    logger.info("Initializing core command modules")

    # Register core command modules
    for cmd_class, cmd_names, description, is_enabled in self.CORE_COMMAND_MODULES:
      # Create an instance of the command class
      cmd_instance = cmd_class()

      # Register the command module
      self.add_command_module(cmd_instance, cmd_names, description, is_enabled)

    logger.info("Core command modules initialized")

  def add_command_module(self, cmd_instance: Any, cmd_names: List[str], description: str, is_enabled: bool = True) -> None:
    """
    Add a command module to the registry.

    Args:
        cmd_instance: The command instance
        cmd_names: List of command names/aliases
        description: Description of the command module
        is_enabled: Whether the command module is enabled
    """
    if not is_enabled:
      logger.info(f"Skipping disabled command module: {cmd_names[0]}")
      return

    logger.debug(f"Adding command module: {cmd_names[0]}")
    self._command_modules[cmd_names[0]] = (cmd_instance, cmd_names, description, is_enabled)

    if is_enabled:
      # Register primary command names
      for name in cmd_names:
        self._command_registry[name] = cmd_instance

      # Register top-level commands if available
      if hasattr(cmd_instance, 'get_top_level_commands'):
        top_level_commands = cmd_instance.get_top_level_commands()
        for cmd_name, cmd_func in top_level_commands.items():
          self._command_registry[cmd_name] = cmd_instance

    logger.info(f"Registered command module: {cmd_names[0]}")

  def initialize_registry(self) -> None:
    """
    Initialize the command registry with currently registered command modules.

    This should be called after all modules have been registered.
    """
    logger.info("Initializing command registry")
    self._command_registry = {}

    # Re-register all enabled command modules
    for cmd_instance, cmd_names, _, is_enabled in self._command_modules.values():
      if is_enabled:
        # Register primary command names
        for name in cmd_names:
          self._command_registry[name] = cmd_instance

        # Register top-level commands if available
        if hasattr(cmd_instance, 'get_top_level_commands'):
          top_level_commands = cmd_instance.get_top_level_commands()
          for cmd_name, cmd_func in top_level_commands.items():
            self._command_registry[cmd_name] = cmd_instance

    logger.info(f"Command registry initialized with {len(self._command_registry)} commands")

  def cleanup_commands(self, commands: List[str], settings: Settings) -> Result:
    """
    Clean up command input by removing empty commands and converting to lowercase.

    Args:
        commands: List of command strings
        settings: Settings object

    Returns:
        Result indicating success or failure
    """
    result: Result = Result()

    if not commands:
      return Result.fail("No command provided.")

    # Prune empty commands
    command_counter = len(commands)
    while command_counter != 0 and len(commands) > 1:
      command_counter -= 1
      if not commands[command_counter]:
        commands.pop(command_counter)

    # Make all commands lowercase
    for index in range(len(commands)):
      commands[index] = commands[index].lower()

    return result

  def get_enabled_command_instances(self) -> List[Any]:
    """
    Get a list of all enabled command instances (without duplicates).

    Returns:
        List of enabled command instances
    """
    return [cmd for cmd, _, _, enabled in self._command_modules.values() if enabled]

  def get_function_definitions(self, settings: Optional[Settings] = None) -> List[Dict[str, Any]]:
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
      for cmd_instance in self.get_enabled_command_instances():
        if hasattr(cmd_instance, 'get_function_definitions'):
          # Make sure we're calling the method, not trying to iterate over it
          cmd_definitions = cmd_instance.get_function_definitions()
          if isinstance(cmd_definitions, list):
            definitions.extend(cmd_definitions)
          else:
            logger.warning(f"get_function_definitions for {cmd_instance.__class__.__name__} did not return a list")
    except Exception as e:
      logger.error(f"Error getting function definitions: {str(e)}")
      # Return an empty list in case of error
      return []

    return definitions

  def execute_command_by_name(self, function_name: str, parameters: Dict[str, Any], settings: Settings) -> str:
    """
    Execute a command by its function name with the given parameters.

    Args:
        function_name: The function name in format "prefix_path_component1_component2_..."
        parameters: Dictionary of parameter values
        settings: Settings object

    Returns:
        Result of the command as a string
    """
    if settings is None:
      return "Error: Settings object is required"

    try:
      # Split the function name into parts (prefix_path_component1_component2_...)
      parts = function_name.split('_')

      if len(parts) < 2:
        return f"Invalid function name format: {function_name}. Expected format: prefix_command_path"

      # The first part is the prefix (class name or module name), the rest is the command path
      prefix = parts[0]
      command_path = parts[1:]

      # Try each enabled command instance
      for cmd_instance in self.get_enabled_command_instances():
        # Determine the prefix for this command instance
        if hasattr(cmd_instance, '_module_name'):
          # This is a module command, use the module name
          instance_prefix = cmd_instance._module_name
        else:
          # This is a core command, use the class name
          instance_prefix = cmd_instance.__class__.__name__.replace("Command", "").lower()

        # Skip if this is not the right command instance
        if instance_prefix != prefix:
          continue

        if hasattr(cmd_instance, 'get_function_definitions'):
          # Get all function definitions from this command instance
          func_defs = cmd_instance.get_function_definitions()

          # Check if our function name matches any of the definitions
          for func_def in func_defs:
            if func_def["name"] == function_name:
              # Found the function, now execute it
              try:
                # Navigate the command tree to find the handler
                current = cmd_instance.function_tree

                for i, part in enumerate(command_path[:-1]):
                  if part in current:
                    current = current[part]
                  else:
                    return f"Invalid command path at part '{part}': {function_name}"

                # The last part should be the function
                last_part = command_path[-1]

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
                  return f"Invalid command function at leaf '{last_part}': {function_name}"
              except Exception as e:
                return f"Error navigating command tree: {str(e)}"
    except Exception as e:
      return f"Error processing command: {str(e)}"

    return f"Unknown function: {function_name}"

  def run(self, input_str: str, settings: Settings) -> Result:
    """
    Run a command from the input string.

    Args:
        input_str: The input command string
        settings: Settings object

    Returns:
        Result of the command execution
    """
    commands = input_str.split()
    result = self.cleanup_commands(commands, settings)

    if result.is_error():
      self.display_help()
    elif commands[0] == "help":
      if len(commands) > 1:
        self.display_command_help(commands[1].lower())
      else:
        self.display_help()
      result = Result()
    elif commands[0] in self._command_registry:
      result = self._command_registry[commands[0]].execute(commands, settings)
    else:
      result = Result.fail("Unrecognized command.")
      self.display_help()

    return result

  def display_help(self) -> None:
    """Display help for all commands."""
    print("Here is a list of available commands:")

    # Display primary command groups
    for cmd_instance, cmd_names, description, is_enabled in self._command_modules.values():
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

    for cmd_instance in self.get_enabled_command_instances():
      if hasattr(cmd_instance, 'get_top_level_commands'):
        for top_cmd, cmd_func in cmd_instance.get_top_level_commands().items():
          top_level_commands.add(top_cmd)
          # Also add aliases
          if hasattr(cmd_func, '_command_aliases'):
            for alias in cmd_func._command_aliases:
              if isinstance(alias, str):
                top_level_commands.add(alias)

    if top_level_commands:
      print("  " + ", ".join(sorted(top_level_commands)))
      print("    - these commands can be used directly without a module prefix")

  def display_command_help(self, command_name: str) -> None:
    """
    Display help for a specific command or module.

    Args:
        command_name: The name of the command
    """
    if command_name in self._command_registry:
      if hasattr(self._command_registry[command_name], 'help'):
        self._command_registry[command_name].help()
      else:
        print(f"No help available for command: {command_name}")
    else:
      print(f"Unknown command: {command_name}")
      self.display_help()
