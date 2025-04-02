"""
This module contains commands for managing agents.
"""

# External dependencies
import logging
from typing import Dict, List, Any

# Internal dependencies
from .base import Command, command
from results import Result
from settings import Settings
from agents import Agent
from enums.agent import AgentType



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

    # Get agent types from enum
    agent_types = [agent_type.value for agent_type in AgentType]

    result.data = agent_types
    result.message = "Available agent types:\n" + "\n".join(agent_types)
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
          "description": "Agent type to use",
          "enum": [agent_type.value for agent_type in AgentType]
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

    try:
      # Convert string to AgentType enum
      agent_enum = AgentType.from_string(agent_type)

      # Store the string value in settings
      settings.active_agent = agent_enum

      result.data = {
        "agent_type": agent_enum.value,
        "agent_name": agent_enum.name
      }
      result.message = f"Agent type set to: {agent_enum.value}"
      return result
    except ValueError as e:
      return Result.fail(str(e))

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
      try:
        result.data = {
          "agent_type": settings.active_agent.value,
          "agent_name": settings.active_agent.name
        }
        result.message = f"Current agent type: {settings.active_agent.value}"
      except ValueError:
        result.data = {"agent_type": settings.active_agent}
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

    try:
      # Convert string to AgentType enum for validation
      agent_enum = AgentType.from_string(agent_type)
      agent_type = agent_enum.value

      # Get all agent types
      agent_types = Agent.get_agent_types()

      # Find the specified agent type
      for agent in agent_types:
        if agent["type"] == agent_type:
          # Build and return the information
          capabilities = ", ".join(agent["capabilities"])
          output = [
            f"Agent Type: {agent['type']}",
            f"Name: {agent['name']}",
            f"Description: {agent['description']}",
            f"Capabilities: {capabilities}"
          ]
          result.data = agent
          result.message = "\n".join(output)
          return result

      return Result.fail(f"Agent type '{agent_type}' found in enum but not registered in Agent system")
    except ValueError as e:
      return Result.fail(str(e))