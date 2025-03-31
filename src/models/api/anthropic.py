from typing import Dict, Any
import logging

# Internal dependencies
from ..base import APIModel
from files import Conversation
from enums import MessageRole



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                               CLASSES                                #
########################################################################
class AnthropicModel(APIModel):
  def __init__(self, model_name: str):
    super().__init__(model_name, base_url="https://api.anthropic.com/v1")
    self.set_custom_header("anthropic-version", "2023-06-01")
    # self.set_custom_header("content-type", "application/json")

  def set_api_key(self, api_key: str) -> None:
    """Set the API key for authentication."""
    self.session.headers.update({"x-api-key": f"{api_key}"})

  def generate(self, conversation: Conversation, **kwargs) -> Conversation:
    """
    Generate text using the Anthropic model with a Conversation object.

    Args:
        conversation: The Conversation object containing messages
        **kwargs: Additional arguments for generation

    Returns:
        str: The generated text response
    """
    # Get user and assistant messages
    conversation_messages = conversation.get_messages([MessageRole.USER, MessageRole.ASSISTANT])

    # Convert to Anthropic format
    formatted_messages = []
    for message in conversation_messages:
      formatted_messages.append({
        "role": message.speaker.value,
        "content": message.content
      })

    data = {
      "model": self.model_name,
      "max_tokens": kwargs.get("max_tokens", 1024),
      "messages": formatted_messages,
    }

    # Add system prompt if found
    if conversation.prompt:
      data["system"] = conversation.prompt

    response = self.post("messages", data)
    response_text = response.json()["content"][0]["text"]

    # Add the response as an assistant message to the conversation
    conversation.add_message(MessageRole.ASSISTANT, response_text)

    return conversation
