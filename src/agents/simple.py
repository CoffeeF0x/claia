"""
SimpleAgent implementation for CLAIA.
A simple agent that directly calls a model for inference.
"""

# External dependencies
import logging
import uuid
import os
from typing import List

# Internal dependencies
from models import run as model_run, ModelCapability, definitions
from enums import MessageRole
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
  def process_request(cls, process) -> object:
    """
    Process a model inference request.

    Args:
        process: The process to execute

    Returns:
        The updated process with results or error information
    """
    try:
      # Get the conversation and settings from the process
      conversation = process.conversation
      settings = process.settings

      if not conversation:
        raise ValueError("Conversation is required for SimpleAgent")

      if not settings:
        raise ValueError("Settings are required for SimpleAgent")

      # Get the model ID from settings or process parameters
      model_id = process.parameters.get("model_id", settings.active_model)
      if not model_id:
        raise ValueError("No active model set in settings")

      # Determine the capability based on the process parameters or model definition
      capability = process.parameters.get("capability")

      # If capability not specified, get it from the model definition
      if not capability and model_id in definitions:
        model_def = definitions[model_id]
        if "capabilities" in model_def and model_def["capabilities"]:
          capability = model_def["capabilities"][0]  # Use the first capability
          logging.debug(f"Using capability {capability} from model definition")

      # Default to text-to-text if still not determined
      if not capability:
        capability = ModelCapability.TTT
        logging.debug("No capability specified, defaulting to text-to-text")

      # Import the function from the main agent module to avoid circular imports
      from agents import process_conversation_for_capability

      # Process the conversation based on the capability
      processed_messages = process_conversation_for_capability(
        capability,
        conversation,
        process.parameters
      )

      # Run the model with the processed messages
      result = model_run(model_id, processed_messages, settings=settings, process_type=capability)

      if result.is_error():
        raise ValueError(f"Error running model: {result.get_message()}")

      # Handle the result based on capability
      if capability == ModelCapability.TTI:
        # Handle image result
        image = result.data

        # Save the generated image
        image_path = os.path.join(settings.artifacts_directory, f"{uuid.uuid4()}.png")
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        image.save(image_path)

        # Add the image to the conversation
        file_id = conversation.add_file(image_path)

        # Add assistant message with the image
        if file_id:
          conversation.add_message(
            MessageRole.ASSISTANT,
            "Here's the generated image:",
            file_paths=[image_path]
          )

          process.mark_completed({
            "response": "Image generated successfully",
            "model": model_id,
            "source": "text-to-image",
            "image_path": image_path,
            "file_id": file_id
          })
        else:
          raise ValueError("Failed to add image to conversation")
      elif capability == ModelCapability.TTA:
        # Handle audio result (placeholder for now)
        process.mark_completed({
          "response": "Audio generation not yet fully implemented",
          "model": model_id,
          "source": "text-to-audio"
        })
      else:
        # Default text response handling
        process.mark_completed({
          "response": result.data,
          "model": model_id,
          "source": capability.value
        })

    except Exception as e:
      logging.exception(f"Error in SimpleAgent for {process.id}: {str(e)}")
      process.mark_failed(str(e))

    return process

  @classmethod
  def get_capabilities(cls) -> List[str]:
    """
    Get a list of SimpleAgent's capabilities.

    Returns:
        A list of capability strings
    """
    return ["text", "image", "audio"]