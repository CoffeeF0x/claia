"""
SimpleAgent implementation for CLAIA.
A simple agent that directly calls a model for inference.
"""

# External dependencies
import logging

# Internal dependencies
from models import run as model_run
from .base import BaseAgent



########################################################################
#                          SIMPLE AGENT CLASS                          #
########################################################################
class SimpleAgent(BaseAgent):
  """
  A simple agent that directly calls a model for inference.

  This agent serves as the central gateway for all direct model interactions,
  translating between agent requests and model capabilities.
  """

  @classmethod
  def process_request(cls, process, **kwargs) -> object:
    """
    Process a model inference request.

    Args:
        process: The process to execute

    Returns:
        The updated process with results or error information
    """
    try:
      # Get the model ID from the validated parameters
      model_id = process.parameters["model_id"]

      # Run the model with the conversation
      result = model_run(model_id, process.conversation, settings=process.settings, **kwargs)

      if result.is_error():
        raise ValueError(f"Error running model: {result.get_message()}")

      process.mark_completed()

    except Exception as e:
      logging.exception(f"Error in SimpleAgent for {process.id}: {str(e)}")
      process.mark_failed(str(e))

    return process