"""
Test Command Functions for CLAIA Demo

These functions simulate the behavior of real tools for demonstration purposes.
"""

import logging
from typing import Dict, Any, Optional

# Setup logger for test commands
logger = logging.getLogger(__name__)


########################################################################
#                           TEST COMMANDS                              #
########################################################################

def echo_command(parameters: Dict[str, Any], settings: Optional[Any] = None) -> str:
  """
  Simulates an echo tool. Returns the input text.

  Args:
    parameters: Expected to contain {'text': 'string to echo'}.
    settings: Optional settings object (unused in this demo command).

  Returns:
    The value of the 'text' parameter or an error message.
  """
  logger.info(f"Executing echo_command with parameters: {parameters}")
  text_to_echo = parameters.get("text")
  if text_to_echo is None:
    logger.warning("Missing 'text' parameter for echo command.")
    return "[ERROR: Missing 'text' parameter for echo]"
  return f"Echo: {text_to_echo}"


def reverse_string_command(parameters: Dict[str, Any], settings: Optional[Any] = None) -> str:
  """
  Simulates a tool that reverses a string.

  Args:
    parameters: Expected to contain {'input_string': 'string to reverse'}.
    settings: Optional settings object (unused in this demo command).

  Returns:
    The reversed string or an error message.
  """
  logger.info(f"Executing reverse_string_command with parameters: {parameters}")
  string_to_reverse = parameters.get("input_string")
  if string_to_reverse is None:
    logger.warning("Missing 'input_string' parameter for reverse_string command.")
    return "[ERROR: Missing 'input_string' parameter for reverse]"
  if not isinstance(string_to_reverse, str):
     logger.warning("'input_string' parameter must be a string.")
     return "[ERROR: 'input_string' must be a string]"
  return string_to_reverse[::-1] 