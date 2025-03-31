import logging
import os

# Internal dependencies
from commands.base import Command, command
from errors import Result
from settings import Settings
from enums import LogLevel, LogFormat
from utilities import clear



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                            COMMAND CLASS                             #
########################################################################
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
    ai_callable=True,
    aliases=["exit", "q"],
    top_level=True
  )
  def quit_app(self, settings: Settings) -> Result:
    """Exit the application"""
    return Result.shutdown()

  @command(
    path=["get", "log-level"],
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
    return f"Current log level: {settings.log_level}"

  @command(
    path=["set", "log-level"],
    description="Set the log level",
    help_text="Set the log level (debug, info, warning, error, critical)",
    parameters={
      "type": "object",
      "properties": {
        "level": {
          "type": "string",
          "description": "Log level to set (debug, info, warning, error, critical)",
          "enum": [level.value for level in LogLevel]
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
    if level in [level.value for level in LogLevel]:
      # Update the settings
      settings.log_level = level

      # Reconfigure logging with the new settings
      settings.configure_logging()

      # Log the change at the new level
      logger = logging.getLogger(__name__)
      logger.debug(f"Log level changed to {level}")

      return f"Log level set to: {level}"
    else:
      return f"Invalid log level. Valid options are: {', '.join(level.value for level in LogLevel)}"

  @command(
    path=["get", "log-format"],
    description="Display the current log format",
    help_text="Display the current log format",
    parameters={
      "type": "object",
      "properties": {}
    },
    returns={
      "type": "string",
      "description": "Current log format"
    },
    ai_callable=True
  )
  def get_log_format(self, settings: Settings) -> str:
    """Display the current log format"""
    return f"Current log format: {settings.log_format}"

  @command(
    path=["set", "log-format"],
    description="Set the log format",
    help_text="Set the log format (simple, standard, detailed)",
    parameters={
      "type": "object",
      "properties": {
        "format": {
          "type": "string",
          "description": "Log format to set (simple, standard, detailed)",
          "enum": [format.value for format in LogFormat]
        }
      },
      "required": ["format"]
    },
    returns={
      "type": "string",
      "description": "Confirmation message"
    },
    ai_callable=True
  )
  def set_log_format(self, settings: Settings, format: str) -> str:
    """Set the log format"""
    format = format.lower()
    if format in [format.value for format in LogFormat]:
      # Update the settings
      settings.log_format = format

      # Reconfigure logging with the new settings
      settings.configure_logging()

      # Log the change
      logger = logging.getLogger(__name__)
      logger.debug(f"Log format changed to {format}")

      return f"Log format set to: {format}"
    else:
      return f"Invalid log format. Valid options are: {', '.join([format.value for format in LogFormat])}"

  @command(
    path=["get", "log-file"],
    description="Display the current log file path",
    help_text="Display the current log file path",
    parameters={
      "type": "object",
      "properties": {}
    },
    returns={
      "type": "string",
      "description": "Current log file path"
    },
    ai_callable=True
  )
  def get_log_file(self, settings: Settings) -> str:
    """Display the current log file path"""
    if settings.log_file:
      return f"Current log file: {settings.log_file}"
    else:
      return "Logging to console only (no log file configured)"

  @command(
    path=["set", "log-file"],
    description="Set the log file path",
    help_text="Set the log file path (empty for console only)",
    parameters={
      "type": "object",
      "properties": {
        "path": {
          "type": "string",
          "description": "Log file path (empty for console only)"
        }
      },
      "required": ["path"]
    },
    returns={
      "type": "string",
      "description": "Confirmation message"
    },
    ai_callable=True
  )
  def set_log_file(self, settings: Settings, path: str) -> str:
    """Set the log file path"""
    # Update the settings
    settings.log_file = path

    # Reconfigure logging with the new settings
    settings.configure_logging()

    # Log the change
    logger = logging.getLogger(__name__)
    if path:
      logger.debug(f"Log file changed to {path}")
      return f"Log file set to: {path}"
    else:
      logger.debug("Logging to console only (log file disabled)")
      return "Logging to console only (log file disabled)"

  @command(
    path=["log", "status"],
    description="Display current logging configuration",
    help_text="Display current logging configuration details",
    parameters={
      "type": "object",
      "properties": {}
    },
    returns={
      "type": "string",
      "description": "Current logging configuration"
    },
    ai_callable=True
  )
  def log_status(self, settings: Settings) -> str:
    """Display current logging configuration"""
    status = [
      "Current Logging Configuration:",
      f"- Log Level: {settings.log_level}",
      f"- Log Format: {settings.log_format}",
    ]

    if settings.log_file:
      status.append(f"- Log File: {settings.log_file}")

      # Check if the log file exists and is writable
      if os.path.exists(settings.log_file):
        status.append(f"  - File exists: Yes")
        status.append(f"  - File size: {os.path.getsize(settings.log_file)} bytes")
        status.append(f"  - Last modified: {os.path.getmtime(settings.log_file)}")
      else:
        status.append(f"  - File exists: No (will be created when logging occurs)")
    else:
      status.append("- Log File: None (console only)")

    # Get information about the root logger
    root_logger = logging.getLogger()
    status.append(f"- Effective Level: {logging.getLevelName(root_logger.getEffectiveLevel())}")
    status.append(f"- Handlers: {len(root_logger.handlers)}")

    for i, handler in enumerate(root_logger.handlers):
      handler_type = handler.__class__.__name__
      handler_level = logging.getLevelName(handler.level)
      status.append(f"  - Handler {i+1}: {handler_type} (Level: {handler_level})")

    return "\n".join(status)
