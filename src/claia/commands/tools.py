"""
Tools commands for Claia

This module provides utility functions that can be called by the AI.
"""

# External dependencies
import datetime
import logging
from typing import Dict, Any, Optional

# Internal dependencies
from .base import Command, command
from results import Result
from settings import Settings



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                            COMMAND CLASS                             #
########################################################################
class ToolsCommand(Command):
  """Command class for utility tool functions"""

  @command(
    path=["time"],
    description="Returns the current time",
    help_text="Get the current time",
    parameters={
      "type": "object",
      "properties": {}
    },
    returns={
      "type": "string",
      "description": "The current time in HH:MM:SS format"
    },
    ai_callable=True
  )
  def get_current_time(self, settings: Settings) -> Result:
    """
    Get the current time.

    Returns:
      Result: Result with the current time in HH:MM:SS format
    """
    result = Result()
    current_time = datetime.datetime.now().strftime("%H:%M:%S")
    result.data = current_time
    result.message = current_time
    return result

  @command(
    path=["date"],
    description="Returns the current date",
    help_text="Get the current date",
    parameters={
      "type": "object",
      "properties": {}
    },
    returns={
      "type": "string",
      "description": "The current date in YYYY-MM-DD format"
    },
    ai_callable=True
  )
  def get_current_date(self, settings: Settings) -> Result:
    """
    Get the current date.

    Returns:
      Result: Result with the current date in YYYY-MM-DD format
    """
    result = Result()
    current_date = datetime.date.today().strftime("%Y-%m-%d")
    result.data = current_date
    result.message = current_date
    return result

  @command(
    path=["username"],
    description="Returns a hardcoded user name",
    help_text="Get the user name",
    parameters={
      "type": "object",
      "properties": {}
    },
    returns={
      "type": "string",
      "description": "The user name"
    },
    ai_callable=True
  )
  def get_user_name(self, settings: Settings) -> Result:
    """
    Get the user name.

    Returns:
      Result: Result with the user name
    """
    result = Result()

    # Use the actual username from settings if available
    if hasattr(settings, "username") and settings.username:
      username = settings.username
    else:
      username = "John Doe"

    result.data = username
    result.message = username
    return result

  @command(
    path=["greet"],
    description="Greets a user by name",
    help_text="Greet a user by name",
    parameters={
      "type": "object",
      "properties": {
        "name": {
          "type": "string",
          "description": "The name of the user to greet"
        }
      },
      "required": ["name"]
    },
    returns={
      "type": "string",
      "description": "A greeting message"
    },
    ai_callable=True
  )
  def greet_user(self, settings: Settings, name: str) -> Result:
    """
    Greet a user by name.

    Args:
      name: The name of the user to greet

    Returns:
      Result: Result with a greeting message
    """
    result = Result()
    greeting = f"Hello, {name}!"
    result.data = greeting
    result.message = greeting
    return result