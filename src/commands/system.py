import logging

from commands.base import Command, command
from errors import Result
from settings import Settings, LOG_LEVELS
from utilities import clear



##################################################
#                 COMMAND CLASS                  #
##################################################
class SystemCommand(Command):

  @command(
    path=["clear"],
    description="Clear the terminal screen",
    help_text="Clear the screen",
    parameters={
      "type": "object",
      "properties": {}
    },
    returns={
      "type": "string",
      "description": "Confirmation message"
    },
    ai_callable=True,
    aliases=["c", "cls"],
    top_level=True
  )
  def clear_screen(self, settings: Settings) -> str:
    """Clear the terminal screen"""
    clear()
    return "Screen cleared"

  @command(
    path=["quit"],
    description="Exit the application",
    help_text="Terminate the clai software",
    parameters={
      "type": "object",
      "properties": {}
    },
    returns={
      "type": "string",
      "description": "Shutdown message"
    },
    ai_callable=False,  # AI shouldn't be able to quit the application
    aliases=["exit", "q"],
    top_level=True
  )
  def quit_app(self, settings: Settings) -> Result:
    """Exit the application"""
    return Result.shutdown()

  @command(
    path=["get", "log_level"],
    description="Display the current log level",
    help_text="Display the current log level",
    parameters={
      "type": "object",
      "properties": {}
    },
    returns={
      "type": "string",
      "description": "Current log level"
    },
    ai_callable=True
  )
  def get_log_level(self, settings: Settings) -> str:
    """Display the current log level"""
    msg = f"Current log level: {settings.log_level}"
    print(msg)
    return msg

  @command(
    path=["set", "log_level"],
    description="Set the log level",
    help_text="Set the log level (debug, info, warning, error, critical)",
    parameters={
      "type": "object",
      "properties": {
        "level": {
          "type": "string",
          "description": "Log level to set (debug, info, warning, error, critical)",
          "enum": list(LOG_LEVELS.keys())
        }
      },
      "required": ["level"]
    },
    returns={
      "type": "string",
      "description": "Confirmation message"
    },
    ai_callable=True
  )
  def set_log_level(self, settings: Settings, level: str) -> str:
    """Set the log level"""
    level = level.lower()
    if level in LOG_LEVELS:
      settings.log_level = level
      logging.getLogger().setLevel(LOG_LEVELS[level])
      msg = f"Log level set to: {level}"
      print(msg)
      return msg
    else:
      msg = f"Invalid log level. Valid options are: {', '.join(LOG_LEVELS.keys())}"
      print(msg)
      return msg
