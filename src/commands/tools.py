"""
Tools commands for Claia

This module provides utility functions that can be called by the AI.
"""

# External dependencies
import datetime
from typing import Dict, Any, Optional

# Internal dependencies
from commands.base import Command, command
from settings import Settings



##################################################
#                   COMMAND CLASS                #
##################################################
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
  def get_current_time(self, settings: Settings) -> str:
    """
    Get the current time.

    Returns:
      str: The current time in HH:MM:SS format
    """
    return datetime.datetime.now().strftime("%H:%M:%S")

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
  def get_current_date(self, settings: Settings) -> str:
    """
    Get the current date.

    Returns:
      str: The current date in YYYY-MM-DD format
    """
    return datetime.date.today().strftime("%Y-%m-%d")

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
  def get_user_name(self, settings: Settings) -> str:
    """
    Get the user name.

    Returns:
      str: The user name
    """
    # Use the actual username from settings if available
    if hasattr(settings, "username") and settings.username:
      return settings.username
    else:
      return "John Doe"

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
  def greet_user(self, settings: Settings, name: str) -> str:
    """
    Greet a user by name.

    Args:
      name: The name of the user to greet

    Returns:
      str: A greeting message
    """
    return f"Hello, {name}!"