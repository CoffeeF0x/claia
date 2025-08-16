"""
BobAgent implementation for CLAIA.
Bob is a gruff, straightforward, no-nonsense assistant with a unique personality.
"""

# External dependencies
import logging
from typing import List

# Internal dependencies
from claia.models import ModelRegistry
from claia.common.enums.model import ModelCapability
from claia.agents.lib import BaseAgent



########################################################################
#                              CONSTANTS                               #
########################################################################
# Bob Agent's system prompt
BOB_SYSTEM_PROMPT = """
You are Bob, a straightforward and no-nonsense assistant.
Bob speaks in the third person and keeps responses brief.
Bob doesn't use flowery language.
Bob is direct and sometimes sarcastic.
Bob always tries to be helpful despite his gruff demeanor.
"""



########################################################################
#                            BOB AGENT CLASS                           #
########################################################################
class BobAgent(BaseAgent):
  """
  Bob is a gruff, straightforward, no-nonsense assistant with a unique personality.

  Bob only works with text-to-text models and has his own system prompt.
  """

  @classmethod
  def process_request(cls, process, **kwargs) -> object:
    """
    Process a request using Bob's unique style.

    Args:
        process: The process to execute

    Returns:
        The updated process with results
    """
    try:
      # Get the validated model ID from parameters
      model_id = process.parameters["model_id"]

      # Check if the model has text-to-text capability using the new registry
      model_registry = ModelRegistry()
      supported_models = model_registry.get_supported_models()
      
      if model_id in supported_models:
        model_def = supported_models[model_id]
        capabilities = model_def.get("capabilities", [])

        if ModelCapability.TTT not in capabilities:
          raise ValueError("Bob only works with text-to-text models")
      else:
        raise ValueError(f"Bob doesn't recognize the model: {model_id}")

      # Set Bob's system prompt
      if process.conversation.prompt != BOB_SYSTEM_PROMPT:
        process.conversation.change_prompt(BOB_SYSTEM_PROMPT)

      # Run the model with the processed messages
      result = cls.model_registry.run(model_id, process.conversation, settings=process.settings, **kwargs)

      if result.is_error():
        raise ValueError(f"Bob ran into a problem: {result.get_message()}")

      process.mark_completed()

    except Exception as e:
      logging.exception(f"Bob encountered an error for {process.id}: {str(e)}")
      process.mark_failed(str(e))

    return process