"""
This module provides a Registry class for managing commands in the CLAIA application.

The Registry is implemented as a singleton to ensure a single point of command registration
and access throughout the application.
"""

# External dependencies
import logging
from typing import Dict, Any, List, Tuple, Optional, Callable

# Internal dependencies
from results import Result
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
class CommandRegistry:
  """
  Singleton class for registering and managing commands in the application.

  The Registry maintains a mapping of command names to their implementations,
  provides methods for command execution, and handles help functionality.
  """
  _instance = None

  # Define core command modules with their associated information
  # Format: (command_class, primary_names, description, is_enabled)
  CORE_COMMAND_MODULES: List[Tuple[Any, List[str], str, bool]] = [
    (
      SystemCommand,
      ["system", "sys", "s"],
      "technical commands such as exiting the program and clearing the screen",
      True
    ),

    (
      ModelCommand,
      ["model", "models"],
      "commands related to selecting and managing language models",
      True
    ),

    (
      ToolsCommand,
      ["tool", "tools"],
      "utility functions such as date, time, and user information",
      True
    ),

    (
      PromptCommand,
      ["prompt", "prompts"],
      "commands related to prompts or system prompts",
      True
    ),

    (
      ConversationCommand,
      ["conversation", "conversations"],
      "commands related to conversations and saved messages",
      True
    ),

    (
      MassedComputeCommand,
      ["massedcompute", "mc"],
      "commands related to deploying and managing GPU instances",
      True
    ),

    (
      AgentCommand,
      ["agent", "agents"],
      "commands related to agent selection and management",
      True
    )
  ]

  def __new__(cls):
    if cls._instance is None:
      cls._instance = super(CommandRegistry, cls).__new__(cls)
      cls._instance._initialized = False
    return cls._instance

  def __init__(self):
    if not self._initialized:
      logger.debug("Initializing Command Registry")
      self._command_map = {}  # Flat map of command_name -> command_details
      self._command_modules = {}  # Module name -> module instance info
      self._initialized = True
      self._initialize_core_commands()

  @property
  def command_map(self) -> Dict[str, Any]:
    """Get the command map dictionary."""
    return self._command_map

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

    # Get module name (primary command name)
    module_name = cmd_names[0]

    logger.debug(f"Adding command module: {module_name}")
    self._command_modules[module_name] = (cmd_instance, cmd_names, description, is_enabled)

    # Determine if this is an external module (has _module_name attribute)
    is_external_module = hasattr(cmd_instance, '_module_name')

    if is_enabled:
      # Register all commands from the module's command map
      if hasattr(cmd_instance, 'command_map'):
        for cmd_name, cmd_details in cmd_instance.command_map.items():
          # For external modules, ensure correct prefix
          if is_external_module and not cmd_name.startswith("modules_"):
            # Add modules_ prefix to avoid naming conflicts
            cmd_name = f"modules_{cmd_name}"

          self._command_map[cmd_name] = {
            "instance": cmd_instance,
            "details": cmd_details
          }
          logger.debug(f"Registered command: {cmd_name}")

      # Register module names as entry points
      for name in cmd_names:
        self._command_map[name] = {
          "instance": cmd_instance,
          "details": {"is_module_entry": True}
        }

      # Register top-level commands for direct execution
      if hasattr(cmd_instance, 'get_top_level_commands'):
        top_level_commands = cmd_instance.get_top_level_commands()
        for cmd_name, cmd_func in top_level_commands.items():
          self._command_map[cmd_name] = {
            "instance": cmd_instance,
            "details": {
              "function": cmd_func,
              "is_top_level": True
            }
          }

    logger.info(f"Registered command module: {module_name} with {len(cmd_instance.command_map) if hasattr(cmd_instance, 'command_map') else 0} commands")

  def cleanup_commands(self, commands: List[str]) -> Result:
    """
    Clean up command input by removing empty commands and converting to lowercase.

    Args:
        commands: List of command strings

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
    Get all command function definitions, including those not marked as AI-callable.

    This method is primarily for internal use and debugging.
    For AI function calling, use get_tool_definitions() instead.

    Args:
        settings: Optional settings object

    Returns:
        List of function definitions in JSON schema format
    """
    definitions = []

    try:
      # Add definitions directly from the command map
      for cmd_name, cmd_entry in self._command_map.items():
        # Skip CLI aliases
        if cmd_name.startswith("cli_"):
          continue

        details = cmd_entry["details"]

        definition = {
          "name": cmd_name,
          "description": details.get("description", ""),
          "parameters": details.get("parameters", {}),
          "returns": details.get("returns", {"type": "string"})
        }
        definitions.append(definition)
    except Exception as e:
      logger.error(f"Error getting function definitions: {str(e)}")
      # Return an empty list in case of error
      return []

    return definitions

  def get_tool_definitions(self, settings: Optional[Settings] = None) -> List[Dict[str, Any]]:
    """
    Get AI-callable tool definitions.

    These are simplified function definitions suitable for AI function calling:
    - Only includes functions marked as ai_callable=True
    - Does not include command aliases
    - Has a consistent structure for parameters and returns

    Args:
        settings: Optional settings object

    Returns:
        List of tool definitions in JSON schema format
    """
    tool_definitions = []

    try:
      # Add definitions directly from the command map
      for cmd_name, cmd_entry in self._command_map.items():
        # Skip CLI aliases
        if cmd_name.startswith("cli_"):
          continue

        details = cmd_entry["details"]

        # Only include AI-callable commands
        if not details.get("ai_callable", False):
          continue

        # Create the tool definition
        tool_definition = {
          "name": cmd_name,
          "description": details.get("description", ""),
          "parameters": details.get("parameters", {}),
          "returns": details.get("returns", {"type": "string"})
        }
        tool_definitions.append(tool_definition)
    except Exception as e:
      logger.error(f"Error getting tool definitions: {str(e)}")
      # Return an empty list in case of error
      return []

    return tool_definitions

  def run(self, input_arg, settings: Settings) -> Result:
    """
    Run a command from either a string input or list of arguments.

    Args:
        input_arg: Either a string command or list of command arguments
        settings: Settings object

    Returns:
        Result of the command execution
    """
    # Convert input to a list of arguments if it's a string
    if isinstance(input_arg, str):
      args = input_arg.split()
    else:
      args = input_arg.copy() if input_arg else []

    # Clean up the commands
    result = self.cleanup_commands(args)
    if result.is_error():
      self.display_help()
      return result

    # Handle empty input
    if not args:
      self.display_help()
      return Result.fail("No command provided")

    # Check for help command
    if args[0] == "help":
      if len(args) > 1:
        self.display_command_help(args[1].lower())
      else:
        self.display_help()
      return Result()

    # Attempt to match and execute command
    cmd_result = self._execute_command(args, settings)
    if cmd_result is not None:
      return cmd_result

    # Unrecognized command
    result = Result.fail(f"Unrecognized command: {args[0]}")
    self.display_help()
    return result

  def _execute_command(self, args: List[str], settings: Settings) -> Optional[Result]:
    """
    Execute a command by attempting different command formats.

    Args:
        args: Command arguments
        settings: Settings object

    Returns:
        Result of command execution, or None if no command matched
    """
    if not args:
      return None

    # First pass: extract arguments and options from all args after args[0]
    command_name = args[0]
    subcommand_parts = []
    positional_args = []
    kwargs = {}

    # Process remaining arguments after command name
    # NOTE: This is not very robust, so we may want to revisit this later
    for i, arg in enumerate(args[1:]):
      if "=" in arg:
        # Key-value parameter
        key, value = arg.split("=", 1)
        kwargs[key] = value
      elif arg.startswith("--"):
        # Flag parameter
        flag_name = arg[2:]
        kwargs[flag_name] = True
      else:
        # Subcommand part or positional argument
        subcommand_parts.append(arg)

    # Check for top-level command
    if command_name in self._command_map:
      cmd_entry = self._command_map[command_name]
      cmd_instance = cmd_entry["instance"]
      cmd_details = cmd_entry["details"]

      if cmd_details.get("is_top_level", False):
        # For top-level commands, check if the command requires args but none provided
        if not subcommand_parts and not kwargs and hasattr(cmd_instance, 'help'):
          # Some commands might need arguments - show command help instead
          if cmd_details.get("requires_args", False):
            cmd_instance.help()
            return Result()

        # Execute top-level command directly with arguments
        func = cmd_details["function"]
        try:
          return func(settings, *subcommand_parts, **kwargs)
        except Exception as e:
          return Result.fail(f"Error executing command: {str(e)}")

      # Handle module entry points (like 'model' or custom modules)
      if cmd_details.get("is_module_entry", False):
        cmd_instance = cmd_entry["instance"]

        if not subcommand_parts:
          # Just the module name, show help
          cmd_instance.help()
          return Result()

        # Continue to module command processing below

    # Check for module command (e.g., "model vllm set zone=us-east1")
    if len(args) >= 2:
      module_name = args[0]

      # Try direct module command lookup
      # First, check if this module exists
      if module_name in self._command_map:
        cmd_entry = self._command_map[module_name]
        cmd_instance = cmd_entry["instance"]

        # If no subcommand parts (only parameters), show help
        if not subcommand_parts:
          cmd_instance.help()
          return Result()

        # Try to find the longest matching subcommand
        found_command = False
        for i in range(len(subcommand_parts), 0, -1):
          # Build potential command key
          cmd_key = '_'.join(subcommand_parts[:i])

          # Determine the appropriate module prefix
          if hasattr(cmd_instance, '_module_name'):
            # External module
            module_prefix = f"modules_{cmd_instance._module_name}"
            full_key = f"{module_prefix}_{cmd_key}"
          else:
            # Built-in module
            module_prefix = cmd_instance.__class__.__name__.replace("Command", "").lower()
            full_key = f"{module_prefix}_{cmd_key}"

          # Check if command exists in registry
          if full_key in self._command_map:
            found_command = True
            # Found a matching command
            cmd_data = self._command_map[full_key]
            func = cmd_data["details"]["function"]

            # Any remaining parts are positional arguments
            remaining_args = subcommand_parts[i:]

            try:
              result = func(settings, *remaining_args, **kwargs)
              if not isinstance(result, Result):
                new_result = Result()
                new_result.message = str(result)
                return new_result
              return result
            except Exception as e:
              logger.exception(f"Error executing command '{full_key}': {str(e)}")
              return Result.fail(f"Error executing command: {str(e)}")

          # Try direct module command lookup with modules_ prefix for external modules
          if hasattr(cmd_instance, '_module_name'):
            direct_module_key = f"modules_{cmd_key}"
            if direct_module_key in self._command_map:
              found_command = True
              cmd_data = self._command_map[direct_module_key]
              func = cmd_data["details"]["function"]

              # Any remaining parts are positional arguments
              remaining_args = subcommand_parts[i:]

              try:
                result = func(settings, *remaining_args, **kwargs)
                if not isinstance(result, Result):
                  new_result = Result()
                  new_result.message = str(result)
                  return new_result
                return result
              except Exception as e:
                logger.exception(f"Error executing command '{direct_module_key}': {str(e)}")
                return Result.fail(f"Error executing command: {str(e)}")

        # If no matching command found but module exists, show module help
        if not found_command:
          logger.info(f"No matching command found for: {' '.join(args)}")
          cmd_instance.help()
          return Result.fail(f"Unknown subcommand: {subcommand_parts[0]}")

    return None

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
    top_level_commands = []

    for cmd_name, cmd_entry in self._command_map.items():
      if cmd_name.startswith("cli_") and cmd_entry["details"].get("is_top_level", False):
        top_level_commands.append(cmd_name[4:])  # Remove 'cli_' prefix

    if top_level_commands:
      print("  " + ", ".join(sorted(top_level_commands)))
      print("    - these commands can be used directly without a module prefix")

  def display_command_help(self, command_name: str) -> None:
    """
    Display help for a specific command or module.

    Args:
        command_name: The name of the command
    """
    # Check if it's a module name
    if command_name in self._command_map:
      cmd_entry = self._command_map[command_name]
      cmd_instance = cmd_entry["instance"]

      if hasattr(cmd_instance, 'help'):
        cmd_instance.help()
      else:
        print(f"No help available for command: {command_name}")
    else:
      print(f"Unknown command: {command_name}")
      self.display_help()