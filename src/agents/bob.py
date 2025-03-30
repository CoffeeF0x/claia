"""
BobAgent implementation for CLAIA.
Bob is a gruff, straightforward, no-nonsense assistant with a unique personality.
"""

# External dependencies
import logging
from typing import List

# Internal dependencies
from models import run as model_run, ModelCapability, definitions
from .base import BaseAgent



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
  def process_request(cls, process) -> object:
    """
    Process a request using Bob's unique style.

    Args:
        process: The process to execute

    Returns:
        The updated process with results
    """
    try:
      # Get the conversation and settings from the process
      conversation = process.conversation
      settings = process.settings

      if not conversation:
        raise ValueError("Bob needs a conversation to work with")

      if not settings:
        raise ValueError("Bob needs settings to function")

      # Get the model ID from settings or process parameters
      model_id = process.parameters.get("model_id", settings.active_model)
      if not model_id:
        raise ValueError("Bob needs a model to use")

      # Check if the model has text-to-text capability
      if model_id in definitions:
        model_def = definitions[model_id]
        capabilities = model_def.get("capabilities", [])

        if ModelCapability.TTT not in capabilities:
          raise ValueError("Bob only works with text-to-text models")
      else:
        raise ValueError(f"Bob doesn't recognize the model: {model_id}")

      # Set or update the system prompt to Bob's prompt
      original_system_prompt = None
      if conversation.system_prompt:
        # Save the original system prompt to restore later
        original_system_prompt = conversation.system_prompt

      # Set Bob's system prompt
      conversation.update_system_prompt(BOB_SYSTEM_PROMPT)

      try:
        # Import the function from the main agent module to avoid circular imports
        from agents import process_conversation_for_capability

        # Process the conversation for text-to-text capability
        processed_messages = process_conversation_for_capability(
          ModelCapability.TTT,
          conversation,
          process.parameters
        )

        # Run the model with the processed messages
        result = model_run(model_id, processed_messages, settings=settings, process_type=ModelCapability.TTT)

        if result.is_error():
          raise ValueError(f"Bob ran into a problem: {result.get_message()}")

        # Complete the process with the result
        process.mark_completed({
          "response": result.data,
          "model": model_id,
          "source": "bob"
        })

      finally:
        # Restore the original system prompt if there was one
        if original_system_prompt:
          conversation.update_system_prompt(original_system_prompt)

    except Exception as e:
      logging.exception(f"Bob encountered an error for {process.id}: {str(e)}")
      process.mark_failed(str(e))

    return process

  @classmethod
  def get_capabilities(cls) -> List[str]:
    """
    Get a list of Bob's capabilities.

    Returns:
        A list of capability strings
    """
    return ["text"]