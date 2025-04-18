from typing import Dict, Any
import logging
import json

# Internal dependencies
from ..base import APIModel
from files import Conversation
from enums import MessageRole



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                              CONSTANTS                               #
########################################################################
ANTHROPIC_API_VERSION = "2023-06-01"



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

  def generate(self, conversation: Conversation, **kwargs) -> str:
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

    # Default to streaming as it's typically preferred
    stream = kwargs.get("stream", True)

    # Build request payload
    data = {
      "model": self.model_name,
      "max_tokens": kwargs.get("max_tokens", 1024),
      "messages": formatted_messages,
      "stream": stream
    }

    # Optional parameters
    if "temperature" in kwargs:
      data["temperature"] = kwargs["temperature"]
    if "top_p" in kwargs:
      data["top_p"] = kwargs["top_p"]
    if "top_k" in kwargs:
      data["top_k"] = kwargs["top_k"]

    # Add system prompt if found
    if conversation.prompt:
      data["system"] = conversation.prompt

    if stream:
      # Add an empty assistant message to the conversation
      message = conversation.add_message(MessageRole.ASSISTANT, "")

      try:
        with self.post("messages", data, stream=True) as response:
          is_first_delta = True
          current_text = ""

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
                  # Append the new text chunk to the message
                  conversation.stream_message(message.message_id, text, append=True)

              # Stop when we see the message_stop event
              elif event_type == "message_stop":
                break

            except json.JSONDecodeError:
              logger.warning(f"Failed to parse Anthropic streaming event: {data_str}")
            except Exception as e:
              logger.error(f"Error processing Anthropic stream: {str(e)}")

      except Exception as e:
        logger.error(f"Failed to stream from Anthropic API: {str(e)}")
        # If streaming fails, try to recover with a regular request
        data["stream"] = False
        response = self.post("messages", data)
        response_text = response.json()["content"][0]["text"]
        conversation.update_message(message.message_id, response_text)
        return response_text

      # Append a newline and mark the end of the stream
      conversation.stream_message(message.message_id, "\n", append=True, end=True)
      return message.content

    else:
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
