"""
Sample module for CLAI application.

This module demonstrates how to create a module with both commands and functions.
"""

# External dependencies
import logging
from typing import Dict, Any

# Internal dependencies
from commands.base import Command, command
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

  @command(
    path=["sample"],
    description="A sample command that demonstrates module functionality",
    help_text="Execute the sample command with optional arguments",
    parameters={
      "type": "object",
      "properties": {
        "args": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Optional arguments for the sample command"
        }
      }
    },
    returns={
      "type": "object",
      "properties": {
        "success": {"type": "boolean"},
        "message": {"type": "string"},
        "data": {"type": "object"}
      }
    },
    ai_callable=True
  )
  def sample_command(self, settings: Settings, *args) -> Result:
    """
    Execute the sample command.

    Args:
      settings: Application settings
      args: Optional command arguments

    Returns:
      Result: Command execution result
    """
    return Result(
      success=True,
      message="Sample command executed successfully!",
      data={"args": list(args) if args else []}
    )

  @command(
    path=["process"],
    description="Process text using the sample module",
    help_text="Process the provided text and return a result",
    parameters={
      "type": "object",
      "properties": {
        "text": {
          "type": "string",
          "description": "Text to process"
        }
      },
      "required": ["text"]
    },
    returns={
      "type": "object",
      "properties": {
        "success": {"type": "boolean"},
        "message": {"type": "string"},
        "data": {"type": "object"}
      }
    },
    ai_callable=True
  )
  def process_text(self, settings: Settings, text: str) -> Dict[str, Any]:
    """
    Process the provided text.

    Args:
      settings: Application settings
      text: Text to process

    Returns:
      Dict[str, Any]: Processing result
    """
    return {
      "success": True,
      "message": f"Sample function executed successfully with text: {text}",
      "data": {"text": text}
    }