# External dependencies
import importlib
from typing import Dict, Any

# Internal dependencies
import help

from commands.characters import CharacterCommand
from commands.conversations import ConversationCommand
from commands.models import ModelCommand
from commands.system import SystemCommand
from commands.massedcompute import MassedComputeCommand
from errors import Result
from settings import Settings

# Try to import the module system
try:
  from modules import get_module_commands
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

# Run the cleanup routine and execute the command
def run(input: str, settings: Settings) -> Result:
  commands = input.split()
  result = cleanup_commands(commands, settings)

  if result.is_error():
    help.allCommands()
  elif (commands[0] in command_registry):
    result = command_registry[commands[0]].execute(commands, settings)
    # if result.is_error():
    #   print(result.get_message())
  else:
    result = Result.fail("Unrecognized command.")
    help.allCommands()

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
