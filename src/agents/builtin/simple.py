"""
Simple agent plugin for CLAIA.
A simple agent that directly calls a model for inference.
"""

# External dependencies
import logging
from typing import Type

# Internal dependencies
from ..lib import BaseAgent, Process
from ..hooks import AgentHooks, AgentInfo


########################################################################
#                          SIMPLE AGENT CLASS                          #
########################################################################
class SimpleAgent(BaseAgent):
  """
  A simple agent that directly calls a model for inference.

  This agent will simply forward requests to the appropriate model.
  """

  @classmethod
  def process_request(cls, process, model_registry=None, **kwargs) -> object:
    """
    Process a model inference request.

    Args:
        process: The process to execute
        model_registry: ModelRegistry instance to use for model operations
        **kwargs: Additional keyword arguments

    Returns:
        The updated process with results or error information
    """
    try:
      # Get the model ID from the validated parameters
      model_id = process.parameters["model_id"]

      # Run the model with the conversation using the provided model registry
      result = model_registry.run(model_id, process.conversation, **kwargs)

      if result.is_error():
        raise ValueError(f"Error running model: {result.get_message()}")

      process.mark_completed(result.get_result())

    except Exception as e:
      logging.exception(f"Error in SimpleAgent for {process.id}: {str(e)}")
      process.mark_failed(str(e))

    return process


########################################################################
#                            PLUGIN HOOKS                              #
########################################################################
class SimpleAgentPlugin:
  """Plugin implementation for the simple agent."""

  def get_agent_class(self, agent_name: str) -> Type[BaseAgent]:
    """Get the agent class for the simple agent."""
    if agent_name.lower() == "simple":
      return SimpleAgent
    return None

  def get_agent_info(self) -> AgentInfo:
    """Get information about the simple agent."""
    return AgentInfo(
      name="simple",
      description="A simple agent that directly calls a model for inference",
      agent_class=SimpleAgent
    )
