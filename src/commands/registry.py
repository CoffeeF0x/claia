import help

from commands.characters import CharacterCommand
from commands.conversations import ConversationCommand
from commands.experimental import ExperimentalCommand
from commands.system import SystemCommand
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

# Run the cleanup routine and execute the command
def run(input: str, settings: Settings) -> Result:
  commands = input.split()
  result = cleanup_commands(commands, settings)

  if result.is_error():
    help.allCommands()
  elif (commands[0] in command_registry):
    result = command_registry[commands[0]].execute(commands, settings)
  else:
    result = Result.fail("Unrecognized command.")
    help.allCommands()

  return result



##################################################
#          COMMAND REGISTRY DEFINITION           #
##################################################
command_registry = {
  "c":             SystemCommand(),
  "clear":         SystemCommand(),
  "cls":           SystemCommand(),
  "q":             SystemCommand(),
  "exit":          SystemCommand(),
  "quit":          SystemCommand(),
  "s":             SystemCommand(),
  "sys":           SystemCommand(),
  "system":        SystemCommand(),

  "character":     CharacterCommand(),
  "characters":    CharacterCommand(),

  "conversation":  ConversationCommand(),
  "conversations": ConversationCommand(),

  "e":  ExperimentalCommand(),
  "exp":  ExperimentalCommand(),
  "experiment":  ExperimentalCommand(),
  "experimental":  ExperimentalCommand(),
}
