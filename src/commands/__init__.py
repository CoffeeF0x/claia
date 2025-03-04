# External dependencies
import importlib
from typing import Dict, Any, List

# Internal dependencies
# from commands.characters import CharacterCommand
# from commands.conversations import ConversationCommand
from commands.models import ModelCommand
from commands.system import SystemCommand
# from commands.massedcompute import MassedComputeCommand
from errors import Result
from settings import Settings



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
  registry = {
    # System commands
    "c":             SystemCommand(),
    "clear":         SystemCommand(),
    "cls":           SystemCommand(),
    "q":             SystemCommand(),
    "exit":          SystemCommand(),
    "quit":          SystemCommand(),
    "s":             SystemCommand(),
    "sys":           SystemCommand(),
    "system":        SystemCommand(),

    # Character commands
    # "character":     CharacterCommand(),
    # "characters":    CharacterCommand(),

    # Conversation commands
    # "conversation":  ConversationCommand(),
    # "conversations": ConversationCommand(),

    # Model commands
    "model":         ModelCommand(),
    "models":        ModelCommand(),

    # MassedCompute commands
    # "mc":            MassedComputeCommand(),
    # "massedcompute": MassedComputeCommand(),
  }

  return registry

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
  for cmd_name, cmd in command_registry.items():
    if hasattr(cmd, 'get_function_definitions'):
      cmd_definitions = cmd.get_function_definitions()
      definitions.extend(cmd_definitions)
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
  # Split the function name into parts (path_component1_component2_...)
  parts = function_name.split('_')

  # Find the command class that handles this function
  for cmd_name, cmd in command_registry.items():
    if hasattr(cmd, 'get_function_definitions'):
      for func_def in cmd.get_function_definitions():
        if func_def["name"] == function_name:
          # Found the function, now navigate the command tree to find the handler
          current = cmd.function_tree
          for part in parts[:-1]:  # All but the last part
            if part in current:
              current = current[part]
            else:
              return f"Invalid command path: {function_name}"

          # The last part should be the function
          last_part = parts[-1]
          if last_part in current and "function" in current[last_part]:
            func = current[last_part]["function"]
            # Call the function with the command instance, settings, and parameters
            return func(cmd, settings, **parameters)
          else:
            return f"Invalid command function: {function_name}"

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
  print("  system, sys, s")
  print("    - technical commands such as exiting the program and clearing the screen")
  print("  character, characters")
  print("    - commands related to characters or system promts")
  print("  conversation, conversations")
  print("    - commands related to conversations and saved messages")
  print("  model, models")
  print("    - commands related to selecting and managing language models")
  print("  massedcompute, mc")
  print("    - commands related to deploying and managing GPU instances")
  print("  help [command|module]")
  print("    - display help information for all commands or a specific command/module")

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