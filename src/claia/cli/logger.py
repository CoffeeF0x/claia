"""
This module handles logging configuration for the CLAIA application.
"""

# External dependencies
import os
import logging

# Internal dependencies
from claia.lib.enums.logging import LogLevel, LogFormat



########################################################################
#                              FUNCTIONS                               #
########################################################################
def initialize_logging(log_level_name: str, log_format_name: str, log_file: str = None) -> logging.Logger:
  """
  Configure the logging system based on the provided settings.

  Args:
    log_level_name: Name of the log level (debug, info, warning, error, critical)
    log_format_name: Name of the log format (simple, standard, detailed)
    log_file: Optional path to a log file (console only if None)

  Returns:
    The configured root logger
  """
  try:
    try:
      log_level = LogLevel.from_string(log_level_name)
    except ValueError:
      print(f"Invalid log level: {log_level_name}. Using default: warning")
      log_level = LogLevel.WARNING

    try:
      log_format = LogFormat.from_string(log_format_name)
    except ValueError:
      print(f"Invalid log format: {log_format_name}. Using default: standard")
      log_format = LogFormat.STANDARD

    # Create a formatter
    formatter = logging.Formatter(log_format.value)

    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.value)

    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
      root_logger.removeHandler(handler)

    # Always add a console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level.name)
    root_logger.addHandler(console_handler)

    # Add a file handler if a log file is specified
    if log_file:
      try:
        # Ensure the directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
          os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level.name)
        root_logger.addHandler(file_handler)

        # Log that we've started logging to a file
        root_logger.info(f"Logging to file: {log_file}")
      except Exception as e:
        root_logger.error(f"Failed to set up file logging to {log_file}: {e}")

    # Log the configuration
    root_logger.debug(f"Logging configured with level={log_level.name}, format={log_format.name}")
    return root_logger

  except Exception as e:
    # Fallback configuration in case of errors
    print(f"Error configuring logging: {e}")
    fallback_logger = logging.getLogger()
    fallback_logger.setLevel(logging.WARNING)

    # Ensure there's at least one handler
    if not fallback_logger.handlers:
      handler = logging.StreamHandler()
      formatter = logging.Formatter('%(levelname)s: %(message)s')
      handler.setFormatter(formatter)
      fallback_logger.addHandler(handler)

    fallback_logger.error(f"Using fallback logging configuration due to error: {e}")
    return fallback_logger
