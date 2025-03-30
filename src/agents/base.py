"""
Base agent class for CLAIA.
Provides a common interface for all agent implementations.
"""

# External dependencies
import logging
from typing import List



########################################################################
#                          BASE AGENT CLASS                            #
########################################################################
class BaseAgent:
  """
  Base agent class that provides a common interface for all agents.

  Agents are responsible for processing requests using different strategies.
  Specific agent implementations should inherit from this class and implement
  the process_request method.
  """

  @classmethod
  def process(cls, process) -> object:
    """
    Process a request and update the process with the result.

    Args:
        process: The process to execute

    Returns:
        The updated process with results or error information
    """
    process.mark_started()

    try:
      return cls.process_request(process)
    except Exception as e:
      logging.exception(f"Error processing {process.id}: {str(e)}")
      process.mark_failed(str(e))
      return process

  @classmethod
  def process_request(cls, process) -> object:
    """
    Implement the actual processing logic for this agent type.
    This method should be overridden by specific agent implementations.

    Args:
        process: The process to execute

    Returns:
        The updated process with results
    """
    raise NotImplementedError("Agent implementations must override process_request")

  @classmethod
  def get_description(cls) -> str:
    """
    Get a description of this agent type.

    Returns:
        A string description of the agent
    """
    return cls.__doc__ or "No description available"

  @classmethod
  def get_capabilities(cls) -> List[str]:
    """
    Get a list of this agent's capabilities.

    Returns:
        A list of capability strings
    """
    return ["process"]