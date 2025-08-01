"""
Agent registry for the CLAIA agents system.

This module provides an AgentRegistry that manages agent plugins and processes requests.
"""

import logging
from typing import Any, Optional, Dict

# Internal dependencies
from common.results import Result
from .lib import Process
from .manager import AgentManager



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                            AGENT REGISTRY                            #
########################################################################
class AgentRegistry:
  """
  Manages agents in the CLAIA application.

  This registry loads agent plugins and dispatches process requests to the
  appropriate agent implementation based on the process's agent_type.
  """

  def __init__(self):
    """Initialize the AgentRegistry."""
    logger.debug("Initializing Agent Registry")

    # Initialize agent manager
    self.manager = AgentManager()

    # Load all plugins
    self.manager.load_all_plugins()

    logger.info("AgentRegistry initialized successfully")

  def process(self, process: Process) -> Process:
    """
    Process the given process by dispatching to the appropriate agent implementation.

    Args:
        process: The process to be executed

    Returns:
        The updated process with results or error information
    """
    try:
      logger.debug(f"Processing {process.id} with agent type '{process.agent_type}'")

      # Get the agent class for this agent type
      agent_class = self.manager.get_agent_class(process.agent_type)

      if not agent_class:
        error_msg = f"No agent found for type '{process.agent_type}'"
        logger.error(error_msg)
        process.mark_failed(error_msg)
        return process

      # Process using the agent class
      logger.debug(f"Using agent class {agent_class.__name__} for {process.id}")
      result = agent_class.process(process)

      return result

    except Exception as e:
      logger.error(f"Error processing {process.id}: {str(e)}")
      process.mark_failed(f"Registry error: {str(e)}")
      return process

  def get_agent_class(self, agent_name: str) -> Optional[type]:
    """
    Get the agent class for a specific agent name.

    Args:
        agent_name: The name of the agent to get the class for

    Returns:
        The agent class that can handle the specified agent type, or None if not found
    """
    return self.manager.get_agent_class(agent_name)
