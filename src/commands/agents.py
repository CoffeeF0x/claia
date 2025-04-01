"""
This module contains commands for managing agents.
"""

# External dependencies
import logging

# Internal dependencies
from commands.base import Command, command
from results import Result
from settings import Settings
from agents import Agent
from enums import AgentType



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                            COMMAND CLASS                             #
########################################################################
class AgentCommand(Command):

  @command(
    path=["list"],
    description="List available agent types",
    help_text="List all available agent types with their descriptions and capabilities"
  )
  def list_agents(self, settings: Settings) -> str:
    """List all available agent types"""
    agent_types = Agent.get_agent_types()

    if not agent_types:
      return "No agent types available"

    # Get the active agent for highlighting
    active_agent = settings.active_agent

    output = []
    for agent in agent_types:
      is_active = agent["type"] == active_agent
      active_marker = "* " if is_active else "  "
      capabilities = ", ".join(agent["capabilities"])
      line = f"{active_marker}{agent['type']}: {agent['description']} (Capabilities: {capabilities})"
      output.append(line)

    return "\n".join(output)

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
  def agent_info(self, settings: Settings, agent_type: str) -> str:
    """Get detailed information about a specific agent type"""
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
        return "\n".join(output)

    return f"Agent type '{agent_type}' not found"

  @command(
    path=["set"],
    description="Set the active agent type",
    help_text="Set the active agent type to use for processing requests",
    parameters={
      "type": "object",
      "properties": {
        "agent_type": {
          "type": "string",
          "description": "The type of agent to set as active"
        }
      },
      "required": ["agent_type"]
    }
  )
  def set_agent(self, settings: Settings, agent_type: str) -> str:
    """Set the active agent type"""
    # Verify that the agent type exists
    try:
      # Check if it's in the enum
      agent_enum = None
      for a_type in AgentType:
        if a_type.value == agent_type:
          agent_enum = a_type
          break

      if not agent_enum:
        return f"Invalid agent type: {agent_type}"

      # Set the active agent
      settings.active_agent = agent_type
      return f"Active agent set to: {agent_type}"
    except Exception as e:
      logger.error(f"Error setting agent type: {e}")
      return f"Error setting agent type: {str(e)}"