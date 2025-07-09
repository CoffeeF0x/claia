import logging
import os
from os import name, system

# Internal dependencies
from .base import Command, command
from results import Result
from settings import Settings
from enums import LogLevel, LogFormat



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


# Clear the console
def clear() -> None:
  if name == "posix":
    system("clear")
  else:
    system("cls")



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
  def clear_screen(self, settings: Settings) -> Result:
    """Clear the terminal screen"""
    result = Result()
    clear()
    result.message = "Screen cleared"
    return result

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
    path=["get"],
    description="Get a system setting value",
    help_text="Get the value of a system setting",
    parameters={
      "type": "object",
      "properties": {
        "setting": {
          "type": "string",
          "description": "The setting to get (log-level, log-format, log-file)",
          "enum": ["log-level", "log-format", "log-file"]
        }
      },
      "required": ["setting"]
    },
    returns={
      "type": "string",
      "description": "Current setting value"
    },
    ai_callable=True
  )
  def get_setting(self, settings: Settings, setting: str) -> Result:
    """Get a system setting value"""
    # Initialize the result object
    result = Result()

    setting = setting.lower().replace('_', '-')

    if setting == "log-level":
      result.message = f"Current log level: {settings.log_level}"
    elif setting == "log-format":
      result.message = f"Current log format: {settings.log_format}"
    elif setting == "log-file":
      if settings.log_file:
        result.message = f"Current log file: {settings.log_file}"
      else:
        result.message = "Logging to console only (no log file configured)"
    else:
      return Result.fail(f"Unknown setting: {setting}")

    return result

  @command(
    path=["set"],
    description="Set a system setting value",
    help_text="Set the value of a system setting",
    parameters={
      "type": "object",
      "properties": {
        "setting": {
          "type": "string",
          "description": "The setting to set (log-level, log-format, log-file)",
          "enum": ["log-level", "log-format", "log-file"]
        },
        "value": {
          "type": "string",
          "description": "The value to set"
        }
      },
      "required": ["setting", "value"]
    },
    returns={
      "type": "string",
      "description": "Confirmation message"
    },
    ai_callable=True
  )
  def set_setting(self, settings: Settings, setting: str, value: str) -> Result:
    """Set a system setting value"""
    setting = setting.lower().replace('_', '-')

    if setting == "log-level":
      return self.set_log_level(settings, level=value)
    elif setting == "log-format":
      return self.set_log_format(settings, format=value)
    elif setting == "log-file":
      return self.set_log_file(settings, file=value)
    else:
      return Result.fail(f"Unknown setting: {setting}")

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
  def get_log_level(self, settings: Settings) -> Result:
    """Display the current log level"""
    result = Result()
    result.message = f"Current log level: {settings.log_level}"
    return result

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
          "enum": [level.name.lower() for level in LogLevel]
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
  def set_log_level(self, settings: Settings, level: str) -> Result:
    """Set the log level"""
    # Initialize the result object
    result = Result()

    # Get logger at the beginning of the function
    logger = logging.getLogger(__name__)

    level = level.lower()
    valid_levels = [lvl.name.lower() for lvl in LogLevel]

    if level in valid_levels:
      # Update the settings
      settings.log_level = level

      # Reconfigure logging if the method exists
      if hasattr(settings, 'configure_logging') and callable(getattr(settings, 'configure_logging')):
        settings.configure_logging()
      else:
        logger.warning("Settings object does not have configure_logging method")

      # Log the change at the new level
      logger.debug(f"Log level changed to {level}")

      # Set success message
      result.message = f"Log level set to: {level}"
      return result
    else:
      # Return error
      return Result.fail(f"Invalid log level: {level}. Valid levels are: {', '.join(valid_levels)}")

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
  def get_log_format(self, settings: Settings) -> Result:
    """Display the current log format"""
    result = Result()
    result.message = f"Current log format: {settings.log_format}"
    return result

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
          "enum": [format.name.lower() for format in LogFormat]
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
  def set_log_format(self, settings: Settings, format: str) -> Result:
    """Set the log format"""
    # Initialize the result object
    result = Result()

    # Get logger at the beginning of the function
    logger = logging.getLogger(__name__)

    format = format.lower()
    valid_formats = [fmt.name.lower() for fmt in LogFormat]

    if format in valid_formats:
      # Update the settings
      settings.log_format = format

      # Reconfigure logging if the method exists
      if hasattr(settings, 'configure_logging') and callable(getattr(settings, 'configure_logging')):
        settings.configure_logging()
      else:
        logger.warning("Settings object does not have configure_logging method")

      # Log the change
      logger.debug(f"Log format changed to {format}")

      result.message = f"Log format set to: {format}"
      return result
    else:
      return Result.fail(f"Invalid log format. Valid options are: {', '.join(valid_formats)}")

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
  def get_log_file(self, settings: Settings) -> Result:
    """Display the current log file path"""
    result = Result()
    if settings.log_file:
      result.message = f"Current log file: {settings.log_file}"
    else:
      result.message = "Logging to console only (no log file configured)"
    return result

  @command(
    path=["set", "log-file"],
    description="Set the log file path",
    help_text="Set the path for log output file",
    parameters={
      "type": "object",
      "properties": {
        "file": {
          "type": "string",
          "description": "Log file path (use 'none' to disable file logging)"
        }
      },
      "required": ["file"]
    },
    returns={
      "type": "string",
      "description": "Confirmation message"
    },
    ai_callable=True
  )
  def set_log_file(self, settings: Settings, file: str) -> Result:
    """Set the log file path"""
    # Initialize the result object
    result = Result()

    # Get logger at the beginning of the function
    logger = logging.getLogger(__name__)

    if file.lower() == "none":
      # Disable file logging
      settings.log_file = None
      if hasattr(settings, 'configure_logging') and callable(getattr(settings, 'configure_logging')):
        settings.configure_logging()
      else:
        logger.warning("Settings object does not have configure_logging method")
      logger.debug("File logging disabled")
      result.message = "File logging disabled"
      return result

    # Ensure the directory exists
    log_dir = os.path.dirname(file)
    if log_dir and not os.path.exists(log_dir):
      try:
        os.makedirs(log_dir)
      except Exception as e:
        return Result.fail(f"Error creating log directory: {str(e)}")

    # Set the log file
    settings.log_file = file
    if hasattr(settings, 'configure_logging') and callable(getattr(settings, 'configure_logging')):
      settings.configure_logging()
    else:
      logger.warning("Settings object does not have configure_logging method")
    logger.debug(f"Log file set to {file}")
    result.message = f"Log file set to: {file}"
    return result

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
  def log_status(self, settings: Settings) -> Result:
    """Display current logging configuration"""
    result = Result()

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

    result.message = "\n".join(status)
    return result
