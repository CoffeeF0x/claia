"""
Anthropic API model implementation.

This module provides the AnthropicModel class for interacting with Anthropic's Claude API,
including support for streaming and non-streaming responses.
"""

import json
import logging
from typing import Dict, Any, Optional

# Internal dependencies
from claia.common.results import Result
from claia.common.files.conversation import Conversation
from claia.common.enums.conversation import MessageRole
from ..base import APIModel


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                               CLASSES                                #
########################################################################
class AnthropicModel(APIModel):
  """Anthropic Claude API model implementation."""

  def __init__(self, model_name: str, anthropic_api_token: Optional[str] = None):
    super().__init__(model_name, "https://api.anthropic.com/v1")
    self.session.headers.update({
      "anthropic-version": "2023-06-01",
      "content-type": "application/json"
    })
    if anthropic_api_token:
      self.set_api_key(anthropic_api_token)

  def set_api_key(self, api_key: str) -> None:
    """Set the API key for Anthropic authentication."""
    self.set_custom_header("x-api-key", api_key)

  def generate(self, conversation: Conversation, **kwargs) -> str:
    """Generate a response using Anthropic's API."""
    try:
      # Get settings
      settings = self.update_settings({}, conversation, **kwargs)

      # Convert conversation to Anthropic format
      system_message, messages = self._convert_conversation_to_messages(conversation)

      # Prepare request data
      request_data = {
        "model": self.model_name,
        "messages": messages,
        "max_tokens": settings.get("max_tokens", 1000),
      }

      # Add system message if present
      if system_message:
        request_data["system"] = system_message

      # Add optional parameters
      if settings.get("temperature") is not None:
        request_data["temperature"] = settings["temperature"]
      if settings.get("top_p") is not None:
        request_data["top_p"] = settings["top_p"]
      if settings.get("top_k") is not None:
        request_data["top_k"] = settings["top_k"]

      # Make API request
      if settings.get("stream", False):
        request_data["stream"] = True
        return self._handle_streaming_response(request_data)
      else:
        return self._handle_non_streaming_response(request_data)

    except Exception as e:
      logger.error(f"Error generating response with Anthropic model {self.model_name}: {e}")
      return f"Error: {str(e)}"

  def _convert_conversation_to_messages(self, conversation: Conversation) -> tuple:
    """Convert a Conversation object to Anthropic messages format."""
    system_message = None
    messages = []

    for message in conversation.messages:
      if message.speaker == MessageRole.SYSTEM:
        # Anthropic uses a separate system parameter
        system_message = message.content
      elif message.speaker == MessageRole.USER:
        messages.append({
          "role": "user",
          "content": message.content
        })
      elif message.speaker == MessageRole.ASSISTANT:
        messages.append({
          "role": "assistant",
          "content": message.content
        })

    return system_message, messages

  def _handle_streaming_response(self, request_data: Dict[str, Any]) -> str:
    """Handle streaming response from Anthropic API."""
    try:
      response = self.post("messages", request_data, stream=True)

      full_response = ""
      for line in response.iter_lines():
        if line:
          line_text = line.decode('utf-8')

          # Anthropic uses Server-Sent Events format
          if line_text.startswith('data: '):
            data_text = line_text[6:]  # Remove 'data: ' prefix

            if data_text.strip() == '[DONE]':
              break

            try:
              data = json.loads(data_text)

              # Handle different event types
              if data.get('type') == 'content_block_delta':
                delta = data.get('delta', {})
                if delta.get('type') == 'text_delta':
                  content = delta.get('text', '')
                  full_response += content
                  print(content, end='', flush=True)
              elif data.get('type') == 'message_delta':
                # Handle message-level deltas if needed
                pass

            except json.JSONDecodeError:
              continue

      return full_response

    except Exception as e:
      logger.error(f"Error in streaming response: {e}")
      return f"Streaming error: {str(e)}"

  def _handle_non_streaming_response(self, request_data: Dict[str, Any]) -> str:
    """Handle non-streaming response from Anthropic API."""
    try:
      response = self.post("messages", request_data)
      data = response.json()

      # Anthropic response format
      if 'content' in data and len(data['content']) > 0:
        # Get the first content block (usually text)
        content_block = data['content'][0]
        if content_block.get('type') == 'text':
          return content_block.get('text', '')

      return "No response generated"

    except Exception as e:
      logger.error(f"Error in non-streaming response: {e}")
      return f"API error: {str(e)}"
