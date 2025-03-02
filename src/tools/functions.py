"""
Tool functions for Claia

This module provides functions that can be called by the AI.
"""

# External dependencies
import datetime
from typing import Dict, Any, List, Optional



##################################################
#                FUNCTION DEFINITIONS            #
##################################################
# Define the functions that can be called by the AI
FUNCTION_DEFINITIONS = [
  {
    "name": "get_current_time",
    "description": "Returns the current time",
    "parameters": {
      "type": "object",
      "properties": {}
    },
    "returns": {
      "type": "string",
      "description": "The current time in HH:MM:SS format"
    }
  },
  {
    "name": "get_current_date",
    "description": "Returns the current date",
    "parameters": {
      "type": "object",
      "properties": {}
    },
    "returns": {
      "type": "string",
      "description": "The current date in YYYY-MM-DD format"
    }
  },
  {
    "name": "get_user_name",
    "description": "Returns a hardcoded user name",
    "parameters": {
      "type": "object",
      "properties": {}
    },
    "returns": {
      "type": "string",
      "description": "The hardcoded user name"
    }
  },
  {
    "name": "greet_user",
    "description": "Greets a user by name",
    "parameters": {
      "type": "object",
      "properties": {
        "name": {
          "type": "string",
          "description": "The name of the user to greet"
        }
      },
      "required": ["name"]
    },
    "returns": {
      "type": "string",
      "description": "A greeting message"
    }
  }
]



##################################################
#                   FUNCTIONS                    #
##################################################
def get_current_time() -> str:
  """
  Get the current time.

  Returns:
    str: The current time in HH:MM:SS format
  """
  return datetime.datetime.now().strftime("%H:%M:%S")

def get_current_date() -> str:
  """
  Get the current date.

  Returns:
    str: The current date in YYYY-MM-DD format
  """
  return datetime.date.today().strftime("%Y-%m-%d")

def get_user_name() -> str:
  """
  Get a hardcoded user name.

  Returns:
    str: The hardcoded user name
  """
  return "John Doe"

def greet_user(name: str) -> str:
  """
  Greet a user by name.

  Args:
    name: The name of the user to greet

  Returns:
    str: A greeting message
  """
  return f"Hello, {name}!" 