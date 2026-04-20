"""
OpenAI API model implementation.

This module provides the OpenAIModel class for interacting with OpenAI's API,
including support for streaming and non-streaming responses.
"""

import json
import logging
from typing import Dict, Any, Optional, Generator

# Internal dependencies
from claia.core.data import Conversation
from claia.core.enums.conversation import MessageRole
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

  def __init__(self, model_name: str, openai_api_token: Optional[str] = None):
    super().__init__(model_name, "https://api.openai.com/v1")
    if openai_api_token:
      self.set_api_key(openai_api_token)

  def generate(self, conversation: Conversation, **kwargs) -> Generator[str, None, str]:
    """Generate a response using OpenAI's API. Yields tokens, returns full response."""
    try:
      settings = self.update_settings({}, conversation, **kwargs)
      messages = self._convert_conversation_to_messages(conversation)

      request_data = {
        "model": self.model_name,
        "messages": messages,
        **{k: v for k, v in settings.items() if v is not None}
      }

      if settings.get("stream", False):
        full_response = yield from self._handle_streaming_response(request_data)
      else:
        full_response = yield from self._handle_non_streaming_response(request_data)

      return full_response

    except Exception as e:
      logger.error(f"Error generating response with OpenAI model {self.model_name}: {e}")
      error_msg = f"Error: {str(e)}"
      yield error_msg
      return error_msg

  def _convert_conversation_to_messages(self, conversation: Conversation) -> list:
    """Convert a Conversation object to OpenAI messages format."""
    messages = []

    system_prompt = conversation.get_system_prompt()
    if system_prompt:
      messages.append({
        "role": "system",
        "content": system_prompt
      })

    for message in conversation.get_thread():
      if message.speaker not in (MessageRole.USER, MessageRole.ASSISTANT):
        continue

      role_mapping = {
        MessageRole.USER: "user",
        MessageRole.ASSISTANT: "assistant"
      }

      openai_role = role_mapping.get(message.speaker, "user")
      messages.append({
        "role": openai_role,
        "content": message.content
      })

    return messages

  def _handle_streaming_response(self, request_data: Dict[str, Any]) -> Generator[str, None, str]:
    """Handle streaming response from OpenAI API. Yields tokens, returns full response."""
    try:
      response = self.post("chat/completions", request_data, stream=True)
      full_response = ""

      for line in response.iter_lines():
        if line:
          line_text = line.decode('utf-8')
          if line_text.startswith('data: '):
            data_text = line_text[6:]

            if data_text.strip() == '[DONE]':
              break

            try:
              data = json.loads(data_text)
              if 'choices' in data and len(data['choices']) > 0:
                delta = data['choices'][0].get('delta', {})
                if 'content' in delta:
                  content = delta['content']
                  full_response += content
                  yield content
            except json.JSONDecodeError:
              continue

      return full_response

    except Exception as e:
      logger.error(f"Error in streaming response: {e}")
      error_msg = f"Streaming error: {str(e)}"
      yield error_msg
      return error_msg

  def _handle_non_streaming_response(self, request_data: Dict[str, Any]) -> Generator[str, None, str]:
    """Handle non-streaming response from OpenAI API. Yields full content as single token."""
    try:
      response = self.post("chat/completions", request_data)
      data = response.json()

      content = ""
      if 'choices' in data and len(data['choices']) > 0:
        content = data['choices'][0]['message']['content']

      response_text = content if content else "No response generated"
      yield response_text
      return response_text

    except Exception as e:
      logger.error(f"Error in non-streaming response: {e}")
      error_msg = f"API error: {str(e)}"
      yield error_msg
      return error_msg
