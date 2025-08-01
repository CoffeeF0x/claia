"""
This module contains the Agent class for CLAIA agent system.
The Agent class is a simple dispatcher that uses the AgentRegistry.

Examples:
    # Process a request
    result = Agent.process(process)
"""

# External dependencies
import logging
from typing import Optional

# Internal dependencies
from .process import Process
from ..registry import AgentRegistry



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                               AGENT                                  #
########################################################################
class Agent:
  """
  Agent class that serves as the entry point for processing requests.

  This class dispatches process requests to the appropriate agent implementation
  using the AgentRegistry and plugin system.
  """

  # Shared registry instance
  _registry: Optional[AgentRegistry] = None

  @classmethod
  def _get_registry(cls) -> AgentRegistry:
    """Get or create the shared registry instance."""
    if cls._registry is None:
      cls._registry = AgentRegistry()
    return cls._registry

  @classmethod
  def process(cls, process: Process) -> Process:
    """
    Process the given process by dispatching to the appropriate agent implementation.

    Args:
        process: The process to be executed

    Returns:
        The updated process with results or error information
    """
    registry = cls._get_registry()
    return registry.process(process)
