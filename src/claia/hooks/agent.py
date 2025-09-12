"""
Hook specifications for agent plugins.
"""

# External dependencies
import pluggy
from typing import Type, Optional, List
from dataclasses import dataclass

# Internal dependencies
from ..lib.base import BaseAgent


########################################################################
#                            DATA CLASSES                              #
########################################################################
@dataclass
class AgentInfo:
  """Information about an agent implementation."""
  name: str
  description: str
  agent_class: Type[BaseAgent]
  required_args: Optional[List[str]] = None  # list of custom args required by the agent


########################################################################
#                            HOOK SPECS                                #
########################################################################
hookspec = pluggy.HookspecMarker("claia_agents")


class AgentHooks:
  """Hook specifications for agent plugins."""

  @hookspec
  def get_agent_class(self, agent_name: str) -> Type[BaseAgent]:
    """
    Get the agent class for a specific agent name.

    Args:
        agent_name: The name of the agent to get the class for

    Returns:
        The agent class that can handle the specified agent type, or None if not supported
    """

  @hookspec
  def get_agent_info(self) -> AgentInfo:
    """
    Get information about this agent plugin.

    Returns:
        AgentInfo object with details about the agent implementation
    """
