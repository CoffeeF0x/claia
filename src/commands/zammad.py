# Internal dependencies
import help

from commands.base import Command
from functions.zammad import *
from errors import Result
from settings import Settings



##################################################
#                 COMMAND CLASS                  #
##################################################
class ZammadCommand(Command):
  def execute(self, commands: list[str], settings: Settings) -> Result:
    result: Result = Result()

    if len(commands) > 1:
      if commands[1] == "list" or commands[1] == "query":
        if len(commands) > 2:
          listTickets(settings, commands[2])
        else:
          listTickets(settings)
      elif commands[1] == "details" and len(commands) > 2:
        getTicketDetails(settings, commands[2])
      elif commands[1] == "test" and len(commands) > 2:
        print(invoke_zammad_api(settings, commands[2]))
      else:
        help.unrecognizedCommand()
    else:
      help.zammadCommands()

    return result
