"""
This module defines enums related to logging levels and formats.
"""

# External dependencies
import logging
from enum import Enum



########################################################################
#                              LOG ENUMS                               #
########################################################################
class LogLevel(Enum):
  """Enum for log levels."""
  DEBUG    = logging.DEBUG
  INFO     = logging.INFO
  WARNING  = logging.WARNING
  ERROR    = logging.ERROR
  CRITICAL = logging.CRITICAL

  @classmethod
  def from_string(cls, level_name: str) -> 'LogLevel':
    """
    Convert a string level name to a LogLevel enum.

    Args:
      level_name: The name of the log level (case insensitive)

    Returns:
      The corresponding LogLevel enum

    Raises:
      ValueError: If the level name is not valid
    """
    level_name = level_name.upper()
    try:
      return cls[level_name]
    except KeyError:
      valid_levels = ", ".join([level.name for level in cls])
      raise ValueError(f"Invalid log level: {level_name}. Valid levels are: {valid_levels}")

class LogFormat(Enum):
  """Enum for log formats."""
  SIMPLE   = "%(levelname)s: %(message)s"
  STANDARD = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  DETAILED = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"

  @classmethod
  def from_string(cls, format_name: str) -> 'LogFormat':
    """
    Convert a string format name to a LogFormat enum.

    Args:
      format_name: The name of the log format (case insensitive)

    Returns:
      The corresponding LogFormat enum

    Raises:
      ValueError: If the format name is not valid
    """
    format_name = format_name.upper()
    try:
      return cls[format_name]
    except KeyError:
      valid_formats = ", ".join([fmt.name for fmt in cls])
      raise ValueError(f"Invalid log format: {format_name}. Valid formats are: {valid_formats}")
