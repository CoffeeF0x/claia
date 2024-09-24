# Internal dependencies
import help

from commands.base import Command
from functions.zammad import ZammadAPI
from errors import Result
from settings import Settings



##################################################
#                 COMMAND CLASS                  #
##################################################
class ZammadCommand(Command):
  def execute(self, commands: list[str], settings: Settings) -> Result:
    result: Result = Result()
    zammad: ZammadAPI = ZammadAPI(settings.zammad_base_url, settings.zammad_api_token)

    if len(commands) > 1:
      if commands[1] == "list" or commands[1] == "query":
        if len(commands) > 2:
          print(zammad.list_tickets(commands[2]))
        else:
          print(zammad.list_tickets())
      elif commands[1] == "details" and len(commands) > 2:
        print(zammad.get_ticket_details(commands[2]))
      elif commands[1] == "test" and len(commands) > 2:
        print(zammad.get(commands[2]))
      else:
        help.unrecognizedCommand()
    else:
      help.zammadCommands()

    return result
