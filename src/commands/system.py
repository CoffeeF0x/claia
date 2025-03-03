import logging

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

    if commands[0] in quit_aliases or (len(commands) > 1 and commands[1] in quit_aliases):
      result = Result.shutdown()
    elif commands[0] in clear_aliases or (len(commands) > 1 and commands[1] in clear_aliases):
      clear()
    elif len(commands) > 1:
      if (len(commands) <= 2 and commands[1] == "get") or (len(commands) <= 3 and commands[1] == "set"):
        print("Unknown or incorrect setting command")
      elif len(commands) > 2 and commands[1] == "get" and commands[2] == "log_level":
        print(f"Current log level: {settings.log_level}")
      elif len(commands) > 3 and commands[1] == "set" and commands[2] == "log_level":
        new_level = commands[3].lower()
        if new_level in Settings.LOG_LEVELS:
          settings.log_level = new_level
          logging.getLogger().setLevel(Settings.LOG_LEVELS[new_level])
          print(f"Log level set to: {new_level}")
        else:
          print(f"Invalid log level. Valid options are: {', '.join(Settings.LOG_LEVELS.keys())}")
      else:
        self.help()
    else:
      self.help()

    return result

  def help(self) -> None:
    print("Here are the available system commands:")
    print("  clear, cls, c")
    print("    - clear the screen")
    print("  quit, exit, q")
    print("    - terminate the clai software")
    print("  get log_level")
    print("    - display the current log level")
    print("  set log_level <level>")
    print("    - set the log level (debug, info, warning, error, critical)")
