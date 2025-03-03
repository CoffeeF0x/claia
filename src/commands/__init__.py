# External dependencies
import importlib
from typing import Dict, Any

# Internal dependencies
from commands.characters import CharacterCommand
from commands.conversations import ConversationCommand
from commands.models import ModelCommand
from commands.system import SystemCommand
from commands.massedcompute import MassedComputeCommand
from errors import Result
from settings import Settings

# Try to import the module system
try:
  from modules import get_module_commands, get_module_list, get_module_help
  HAS_MODULE_SYSTEM = True
except ImportError:
  HAS_MODULE_SYSTEM = False



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
    "character":     CharacterCommand(),
    "characters":    CharacterCommand(),

    # Conversation commands
    "conversation":  ConversationCommand(),
    "conversations": ConversationCommand(),

    # Model commands
    "model":         ModelCommand(),
    "models":        ModelCommand(),

    # MassedCompute commands
    "mc":            MassedComputeCommand(),
    "massedcompute": MassedComputeCommand(),
  }

  # Add module commands if the module system is available
  if HAS_MODULE_SYSTEM:
    try:
      module_commands = get_module_commands()
      registry.update(module_commands)
    except Exception as e:
      print(f"Error loading module commands: {e}")

  return registry



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

  # List available modules if the module system is available
  if HAS_MODULE_SYSTEM:
    try:
      modules = get_module_list()

      if modules:
        print("\nAvailable modules:")
        for module in modules:
          print(f"  {module}")
        print("  Use 'help <module>' for module-specific help")
    except Exception as e:
      print(f"Error listing modules: {e}")

# Display help for a specific command or module
def display_command_help(command_name: str) -> None:
  if command_name in command_registry:
    command_registry[command_name].help()
  elif command_name == "modules" and HAS_MODULE_SYSTEM:
    try:
      from modules import help as modules_help
      print(modules_help())
    except Exception as e:
      print(f"Error displaying module system help: {e}")
  elif HAS_MODULE_SYSTEM:
    try:
      module_commands = get_module_commands()

      if command_name in module_commands:
        # Try to get module-specific help
        module_help = get_module_help(command_name)
        if module_help:
          print(module_help)
        else:
          print(f"No help available for module: {command_name}")
      else:
        print(f"Unknown command or module: {command_name}")
        display_help()
    except Exception as e:
      print(f"Error displaying module help: {e}")
      display_help()
  else:
    print(f"Unknown command: {command_name}")
    display_help()
