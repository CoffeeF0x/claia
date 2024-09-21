import help

from commands.base import Command
from errors import Result
from settings import Settings
from utilities import clear



##################################################
#                 COMMAND CLASS                  #
##################################################
class SystemCommand(Command):
  def execute(self, commands: list[str], settings: Settings) -> Result:
    result: Result = Result()

    quit_aliases = ["q", "quit", "exit"]
    clear_aliases = ["c", "cls", "clear"]

    if commands[0] in quit_aliases:
      result = Result.shutdown()
    elif commands[0] in clear_aliases:
      clear()
    elif len(commands) > 1:
      if commands[1] in quit_aliases:
        result = result.shutdown()
      elif commands[1] in clear_aliases:
        clear()
    else:
      help.systemCommands()

    return result
