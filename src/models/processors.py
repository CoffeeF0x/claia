# External dependencies
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, TypeVar, Generic

# Internal dependencies
from models.base import APIModel, LocalModel
from models.definitions import ModelCapability, IOType
from conversations import Conversation
from errors import Result



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                           BASE PROCESSOR                             #
########################################################################
class ModelProcessor(ABC):
  """Base class for all model processors."""

  def __init__(self, model: Any):
    self.model = model

  @abstractmethod
  def process(self, conversation: Conversation, settings: Any = None) -> Result:
    """
    Process a conversation using the model.

    Args:
        conversation: The conversation to process
        settings: Optional settings object

    Returns:
        Result object containing the model's response
    """
    pass



########################################################################
#                        TEXT TO TEXT PROCESSOR                        #
########################################################################
class TextToTextProcessor(ModelProcessor):
  """Processor for text-to-text models."""

  def process(self, conversation: Conversation, settings: Any = None) -> Result:
    """
    Process a conversation using a text-to-text model.

    Args:
        conversation: The conversation to process
        settings: Optional settings object

    Returns:
        Result object containing the model's response
    """
    try:
      # Get formatted messages from the conversation
      messages = conversation.get_formatted_messages()

      # Validate messages
      if not messages or not isinstance(messages, list):
        return Result.fail("Text-to-text requires a list of messages")

      # Generate response using the model
      response = self.model.generate(messages)
      return Result(data=response)
    except Exception as e:
      logger.error(f"Error processing text-to-text request: {str(e)}")
      return Result.fail(f"Failed to process text-to-text request: {str(e)}")



########################################################################
#                       TEXT TO IMAGE PROCESSOR                        #
########################################################################
class TextToImageProcessor(ModelProcessor):
  """Processor for text-to-image models."""

  def process(self, conversation: Conversation, settings: Any = None) -> Result:
    """
    Process a conversation using a text-to-image model.

    Args:
        conversation: The conversation to process
        settings: Optional settings object

    Returns:
        Result object containing the generated image data
    """
    try:
      # Get formatted messages from the conversation
      messages = conversation.get_formatted_messages()

      # Extract the prompt from the last user message
      prompt = None
      for message in reversed(messages):
        if message.get('role') == 'user':
          prompt = message.get('content', '')
          break

      # Validate prompt
      if not prompt or not isinstance(prompt, str):
        return Result.fail("Text-to-image requires a non-empty prompt")

      # TODO: Implement actual image generation call
      # Example implementation:
      # image_data = self.model.generate_image(prompt)
      # return Result(data=image_data)

      return Result.fail("Text-to-image processing not yet implemented")
    except Exception as e:
      logger.error(f"Error processing text-to-image request: {str(e)}")
      return Result.fail(f"Failed to process text-to-image request: {str(e)}")



########################################################################
#                        TEXT TO AUDIO PROCESSOR                       #
########################################################################
class TextToAudioProcessor(ModelProcessor):
  """Processor for text-to-audio models."""

  def process(self, conversation: Conversation, settings: Any = None) -> Result:
    """
    Process a conversation using a text-to-audio model.

    Args:
        conversation: The conversation to process
        settings: Optional settings object

    Returns:
        Result object containing the generated audio data
    """
    try:
      # Get formatted messages from the conversation
      messages = conversation.get_formatted_messages()

      # Extract the text from the last user message
      text = None
      for message in reversed(messages):
        if message.get('role') == 'user':
          text = message.get('content', '')
          break

      # Validate text
      if not text or not isinstance(text, str):
        return Result.fail("Text-to-audio requires non-empty text")

      # TODO: Implement actual audio generation call
      # Example implementation:
      # audio_data = self.model.generate_audio(text)
      # return Result(data=audio_data)

      return Result.fail("Text-to-audio processing not yet implemented")
    except Exception as e:
      logger.error(f"Error processing text-to-audio request: {str(e)}")
      return Result.fail(f"Failed to process text-to-audio request: {str(e)}")



########################################################################
#                       IMAGE TO TEXT PROCESSOR                        #
########################################################################
class ImageToTextProcessor(ModelProcessor):
  """Processor for image-to-text models."""

  def process(self, conversation: Conversation, settings: Any = None) -> Result:
    """
    Process a conversation using an image-to-text model.

    Args:
        conversation: The conversation to process
        settings: Optional settings object

    Returns:
        Result object containing the generated text description
    """
    try:
      # Get formatted messages from the conversation
      messages = conversation.get_formatted_messages()

      # Find image data in the conversation
      # This would typically be in the metadata or attached files
      image_data = None
      prompt = None

      # Extract prompt from the last user message
      for message in reversed(messages):
        if message.get('role') == 'user':
          prompt = message.get('content', '')
          break

      # In a real implementation, we would extract image data from the conversation
      # For now, we'll just return an error
      if not image_data:
        return Result.fail("Image-to-text requires image data")

      # TODO: Implement actual image-to-text call
      # Example implementation:
      # text = self.model.describe_image(image_data, prompt)
      # return Result(data=text)

      return Result.fail("Image-to-text processing not yet implemented")
    except Exception as e:
      logger.error(f"Error processing image-to-text request: {str(e)}")
      return Result.fail(f"Failed to process image-to-text request: {str(e)}")