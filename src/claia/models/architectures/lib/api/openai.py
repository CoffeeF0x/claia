"""
OpenAI API model implementation.

This module provides the OpenAIModel class for interacting with OpenAI's API,
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
class OpenAIModel(APIModel):
  """OpenAI API model implementation."""

  def __init__(self, model_name: str, api_key: Optional[str] = None):
    super().__init__(model_name, "https://api.openai.com/v1")
    if api_key:
      self.set_api_key(api_key)

  def generate(self, conversation: Conversation, **kwargs) -> str:
    """Generate a response using OpenAI's API."""
    try:
      # Get settings
      settings = self.update_settings({}, conversation, **kwargs)

      # Convert conversation to OpenAI format
      messages = self._convert_conversation_to_messages(conversation)

      # Prepare request data
      request_data = {
        "model": self.model_name,
        "messages": messages,
        **{k: v for k, v in settings.items() if v is not None}
      }

      # Make API request
      if settings.get("stream", False):
        return self._handle_streaming_response(request_data)
      else:
        return self._handle_non_streaming_response(request_data)

    except Exception as e:
      logger.error(f"Error generating response with OpenAI model {self.model_name}: {e}")
      return f"Error: {str(e)}"

  def _convert_conversation_to_messages(self, conversation: Conversation) -> list:
    """Convert a Conversation object to OpenAI messages format."""
    messages = []

    for message in conversation.messages:
      role_mapping = {
        MessageRole.SYSTEM: "system",
        MessageRole.USER: "user",
        MessageRole.ASSISTANT: "assistant"
      }

      openai_role = role_mapping.get(message.speaker, "user")
      messages.append({
        "role": openai_role,
        "content": message.content
      })

    return messages

  def _handle_streaming_response(self, request_data: Dict[str, Any]) -> str:
    """Handle streaming response from OpenAI API."""
    try:
      response = self.post("chat/completions", request_data, stream=True)

      full_response = ""
      for line in response.iter_lines():
        if line:
          line_text = line.decode('utf-8')
          if line_text.startswith('data: '):
            data_text = line_text[6:]  # Remove 'data: ' prefix

            if data_text.strip() == '[DONE]':
              break

            try:
              data = json.loads(data_text)
              if 'choices' in data and len(data['choices']) > 0:
                delta = data['choices'][0].get('delta', {})
                if 'content' in delta:
                  content = delta['content']
                  full_response += content
                  print(content, end='', flush=True)
            except json.JSONDecodeError:
              continue

      return full_response

    except Exception as e:
      logger.error(f"Error in streaming response: {e}")
      return f"Streaming error: {str(e)}"

  def _handle_non_streaming_response(self, request_data: Dict[str, Any]) -> str:
    """Handle non-streaming response from OpenAI API."""
    try:
      response = self.post("chat/completions", request_data)
      data = response.json()

      if 'choices' in data and len(data['choices']) > 0:
        return data['choices'][0]['message']['content']
      else:
        return "No response generated"

    except Exception as e:
      logger.error(f"Error in non-streaming response: {e}")
      return f"API error: {str(e)}"
