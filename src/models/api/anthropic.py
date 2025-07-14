from typing import Dict, Any, List
import logging
import json

# Internal dependencies
from ..base import APIModel
from common.files.conversation import Conversation
from common.enums.conversation import MessageRole



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                              CONSTANTS                               #
########################################################################
ANTHROPIC_API_VERSION = "2023-06-01"

# Anthropic-specific default settings
DEFAULT_SETTINGS = {
  "max_tokens": 1024,
}



########################################################################
#                               CLASSES                                #
########################################################################
class AnthropicModel(APIModel):
  def __init__(self, model_name: str):
    super().__init__(model_name, base_url="https://api.anthropic.com/v1")
    self.set_custom_header("anthropic-version", ANTHROPIC_API_VERSION)
    self.set_custom_header("content-type", "application/json")

  def set_api_key(self, api_key: str) -> None:
    """Set the API key for authentication."""
    self.set_custom_header("x-api-key", api_key)

  def _format_messages(self, conversation: Conversation) -> List[Dict[str, Any]]:
    """
    Format conversation messages for the Anthropic API.

    Args:
        conversation: The conversation containing messages

    Returns:
        List[Dict[str, Any]]: Formatted messages for the API request
    """
    messages = []

    # Convert to Anthropic format
    # NOTE: Anthropic API requires non-empty user messages
    for message in conversation.get_messages([MessageRole.USER, MessageRole.ASSISTANT]):
      if message.content == "" and message.speaker == MessageRole.USER:
        continue
      messages.append({
        "role": message.speaker.value,
        "content": message.content.strip()
      })

    return messages

  def generate(self, conversation: Conversation, **kwargs) -> str:
    """
    Generate text using the Anthropic model with a Conversation object.

    Args:
        conversation: The Conversation object containing messages
        **kwargs: Additional arguments for generation

    Returns:
        str: The generated text response
    """
    settings = self.update_settings(DEFAULT_SETTINGS, conversation, **kwargs)
    messages = self._format_messages(conversation)

    # Build request payload
    data = {
      "model": self.model_name,
      "max_tokens": settings.get("max_tokens"),
      "messages": messages,
      "stream": settings.get("stream")
    }

    # Add optional parameters
    if settings.get("temperature"):
      data["temperature"] = settings.get("temperature")
    # if settings.get("top_p"):
    #   data["top_p"] = settings.get("top_p")
    # if settings.get("top_k"):
    #   data["top_k"] = settings.get("top_k")
    # if settings.get("n"):
    #   data["n"] = settings.get("n")
    # if settings.get("stop"):
    #   data["stop"] = settings.get("stop")

    # Add system prompt if found
    if conversation.prompt:
      data["system"] = conversation.prompt

    # Call the appropriate method based on whether streaming is enabled
    if settings.get("stream"):
      return self._get_text_stream(data, conversation)
    else:
      return self._get_text(data, conversation)

  def _get_text_stream(self, data: Dict[str, Any], conversation: Conversation) -> str:
    """
    Get streaming response from the Anthropic API.

    Args:
        data: The request payload
        conversation: The conversation to update with streamed content

    Returns:
        str: The complete generated text
    """
    # Add an empty assistant message to the conversation
    message = conversation.add_message(MessageRole.ASSISTANT, "")
    response = self.post("messages", data, stream=True)

    # Process the streaming response
    for line in response.iter_lines():
      if not line:
        continue

      line = line.decode('utf-8') if isinstance(line, bytes) else line

      if not line.startswith('data: '):
        continue

      data_str = line[6:]

      try:
        event = json.loads(data_str)
        event_type = event.get("type")

        # Handle content_block_delta events (the actual text chunks)
        if event_type == "content_block_delta":
          delta = event.get("delta", {})
          text = delta.get("text", "")

          if text:
            conversation.stream_message(message.message_id, text, append=True)

        # Stop when we see the message_stop event
        elif event_type == "message_stop":
          break

      except json.JSONDecodeError:
        logger.warning(f"Failed to parse Anthropic streaming event: {data_str}")

    # Append a newline and mark the end of the stream
    conversation.stream_message(message.message_id, "\n", append=True, end=True)
    return message.content

  def _get_text(self, data: Dict[str, Any], conversation: Conversation) -> str:
    """
    Get non-streaming response from the Anthropic API.

    Args:
        data: The request payload
        conversation: The conversation to update with the response

    Returns:
        str: The generated text
    """
    # Non-streaming mode
    try:
      response = self.post("messages", data)
      response_json = response.json()

      if "content" in response_json and len(response_json["content"]) > 0:
        content_block = response_json["content"][0]
        if "text" in content_block:
          response_text = content_block["text"]
          conversation.add_message(MessageRole.ASSISTANT, response_text)
          return response_text

      logger.error(f"Unexpected response format from Anthropic: {response_json}")
      error_message = "Error: Invalid response from Anthropic API"
      return error_message

    except Exception as e:
      logger.error(f"Error calling Anthropic API: {str(e)}")
      error_message = f"Error: {str(e)}"
      return error_message
