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