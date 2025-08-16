"""
This module contains commands for managing agents.
"""

# External dependencies
import logging
from typing import Dict, List, Any

# Internal dependencies
from .base import Command, command
from claia.common.results import Result
from claia.cli.settings import Settings
from claia.agents import AgentRegistry



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                            COMMAND CLASS                             #
########################################################################
class AgentCommand(Command):
  """Agent command implementation"""

  @command(
    path=["list"],
    description="List all available agent types",
    help_text="List all available agent types that can be selected",
    parameters={
      "type": "object",
      "properties": {}
    },
    returns={
      "type": "string",
      "description": "List of available agent types"
    },
    ai_callable=True
  )
  def list_agents(self, settings: Settings) -> Result:
    """List all available agent types"""
    result = Result()

    # Get agent types from the Agent registry
    agent_types = Agent.get_agent_types()
    agent_type_values = [agent["type"] for agent in agent_types]

    result.data = agent_type_values
    result.message = "Available agent types:\n" + "\n".join(agent_type_values)
    return result

  @command(
    path=["set"],
    description="Set the current agent type",
    help_text="Set the agent type to use for interactions",
    parameters={
      "type": "object",
      "properties": {
        "agent_type": {
          "type": "string",
          "description": "Agent type to use"
        }
      },
      "required": ["agent_type"]
    },
    returns={
      "type": "string",
      "description": "Confirmation message"
    },
    ai_callable=True
  )
  def set_agent(self, settings: Settings, agent_type: str) -> Result:
    """Set the agent type to use"""
    result = Result()

    # Get all available agent types
    agent_types = Agent.get_agent_types()
    agent_type_values = [agent["type"] for agent in agent_types]

    # Check if the agent type exists
    agent_type_lower = agent_type.lower()
    if agent_type_lower not in [t.lower() for t in agent_type_values]:
      return Result.fail(f"Invalid agent type: {agent_type}. Valid types are: {', '.join(agent_type_values)}")

    # Store the agent type in settings
    settings.active_agent = agent_type_lower

    result.data = {
      "agent_type": agent_type_lower
    }
    result.message = f"Agent type set to: {agent_type_lower}"
    return result

  @command(
    path=["current"],
    description="Show the current agent type",
    help_text="Display the currently selected agent type",
    parameters={
      "type": "object",
      "properties": {}
    },
    returns={
      "type": "string",
      "description": "Current agent type"
    },
    ai_callable=True
  )
  def current_agent(self, settings: Settings) -> Result:
    """Show the current agent type"""
    result = Result()

    if settings.active_agent:
      result.data = {
        "agent_type": settings.active_agent
      }
      result.message = f"Current agent type: {settings.active_agent}"
    else:
      result.message = "No agent type selected"

    return result

  @command(
    path=["remove"],
    description="Remove the current agent selection",
    help_text="Remove the current agent selection",
    parameters={
      "type": "object",
      "properties": {}
    },
    returns={
      "type": "string",
      "description": "Confirmation message"
    },
    ai_callable=True
  )
  def remove_agent(self, settings: Settings) -> Result:
    """Remove the current agent selection"""
    result = Result()

    settings.active_agent = None
    result.message = "Agent selection removed"

    return result

  @command(
    path=["info"],
    description="Get information about a specific agent type",
    help_text="Get detailed information about a specific agent type",
    parameters={
      "type": "object",
      "properties": {
        "agent_type": {
          "type": "string",
          "description": "The type of agent to get information about"
        }
      },
      "required": ["agent_type"]
    }
  )
  def agent_info(self, settings: Settings, agent_type: str) -> Result:
    """Get detailed information about a specific agent type"""
    result = Result()

    # Get all agent types
    agent_types = Agent.get_agent_types()

    # Find the specified agent type (case-insensitive)
    agent_type_lower = agent_type.lower()
    for agent in agent_types:
      if agent["type"].lower() == agent_type_lower:
        # Build and return the information
        output = [
          f"Agent Type: {agent['type']}",
          f"Name: {agent['name']}",
          f"Description: {agent['description']}"
        ]
        result.data = agent
        result.message = "\n".join(output)
        return result

    # If not found, get all available types for the error message
    available_types = [agent["type"] for agent in agent_types]
    return Result.fail(f"Agent type '{agent_type}' not found. Available types: {', '.join(available_types)}")