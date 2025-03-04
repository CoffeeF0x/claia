"""
Sample module for CLAI application.

This module demonstrates how to create a module with both commands and functions.
"""

# External dependencies
import logging
from typing import Dict, Any

# Internal dependencies
from commands.base import Command
from errors import Result
from settings import Settings



##################################################
#                   CONSTANTS                    #
##################################################
logger = logging.getLogger(__name__)



##################################################
#                   COMMANDS                     #
##################################################
class ModuleCommands(Command):
  """A sample command that demonstrates how to create a module command."""

  def execute(self, commands: list[str], settings: Settings) -> Result:
    """
    Execute the sample command.

    Args:
      commands: List of command arguments
      settings: Application settings

    Returns:
      Result: Command execution result
    """
    return Result(
      success=True,
      message="Sample command executed successfully!",
      data={"args": commands[1:] if len(commands) > 1 else []}
    )

  def help(self) -> str:
    """Return help information for the command."""
    return "sample - A sample command that demonstrates module functionality"



##################################################
#                   FUNCTIONS                    #
##################################################
def sample_function(text: str) -> Dict[str, Any]:
  """
  A sample function that demonstrates how to create a module function.

  Args:
    text: Text to process

  Returns:
    Dict[str, Any]: Function result
  """
  return {
    "success": True,
    "message": f"Sample function executed successfully with text: {text}",
    "data": {"text": text}
  }



##################################################
#                MODULE EXPORTS                  #
##################################################
# List of function definitions to be loaded by the module system
FUNCTION_DEFINITIONS = [
  {
    "name": "sample_function",
    "description": "A sample function that demonstrates module functionality",
    "parameters": {
      "type": "object",
      "properties": {
        "text": {
          "type": "string",
          "description": "Text to process"
        }
      },
      "required": ["text"]
    }
  }
] 