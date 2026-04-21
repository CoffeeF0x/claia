"""
Anthropic API model implementation.

This module provides the AnthropicModel class for interacting with Anthropic's Claude API,
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
#                            CONSTANTS                               #
########################################################################
REFUSAL_NOTE = "\n\n[Note: Claude declined to complete this response for safety reasons]"



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

  def generate(self, conversation: Conversation, **kwargs) -> Generator[str, None, str]:
    """Generate a response using Anthropic's API. Yields tokens, returns full response."""
    try:
      settings = self.update_settings({}, **kwargs)
      system_message, messages = self._convert_conversation_to_messages(conversation)

      request_data = {
        "model": self.model_name,
        "messages": messages,
        "max_tokens": settings.get("max_tokens", 1000),
      }

      if system_message:
        request_data["system"] = system_message

      # Anthropic rejects requests that include both temperature and top_p.
      # Prefer temperature; only send top_p when temperature is absent.
      temperature = settings.get("temperature")
      top_p = settings.get("top_p")
      top_k = settings.get("top_k")

      if temperature is not None:
        request_data["temperature"] = temperature
      elif top_p is not None:
        request_data["top_p"] = top_p

      if top_k is not None:
        request_data["top_k"] = top_k

      if settings.get("stream", False):
        request_data["stream"] = True
        full_response = yield from self._handle_streaming_response(request_data)
      else:
        full_response = yield from self._handle_non_streaming_response(request_data)

      return full_response

    except Exception as e:
      logger.error(f"Error generating response with Anthropic model {self.model_name}: {e}")
      error_msg = f"Error: {str(e)}"
      yield error_msg
      return error_msg

  def _convert_conversation_to_messages(self, conversation: Conversation) -> tuple:
    """Convert a Conversation object to Anthropic messages format."""
    system_message = conversation.get_system_prompt()
    messages = []

    for message in conversation.get_thread():
      if message.speaker == MessageRole.USER:
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

  def _handle_streaming_response(self, request_data: Dict[str, Any]) -> Generator[str, None, str]:
    """Handle streaming response from Anthropic API. Yields tokens, returns full response."""
    try:
      response = self.post("messages", request_data, stream=True)
      full_response = ""
      stop_reason = None

      for line in response.iter_lines():
        if line:
          line_text = line.decode('utf-8')

          if line_text.startswith('data: '):
            data_text = line_text[6:]

            if data_text.strip() == '[DONE]':
              break

            try:
              data = json.loads(data_text)

              if data.get('type') == 'content_block_delta':
                delta = data.get('delta', {})
                if delta.get('type') == 'text_delta':
                  content = delta.get('text', '')
                  full_response += content
                  yield content
              elif data.get('type') == 'message_delta':
                delta = data.get('delta', {})
                if 'stop_reason' in delta:
                  stop_reason = delta['stop_reason']

            except json.JSONDecodeError:
              continue

      if stop_reason == 'refusal':
        logger.warning("Claude refused to generate content for safety reasons")
        yield REFUSAL_NOTE
        full_response += REFUSAL_NOTE

      return full_response

    except Exception as e:
      logger.error(f"Error in streaming response: {e}")
      error_msg = f"Streaming error: {str(e)}"
      yield error_msg
      return error_msg

  def _handle_non_streaming_response(self, request_data: Dict[str, Any]) -> Generator[str, None, str]:
    """Handle non-streaming response from Anthropic API. Yields full content as single token."""
    try:
      response = self.post("messages", request_data)
      data = response.json()

      content = ""
      if 'content' in data and len(data['content']) > 0:
        content_block = data['content'][0]
        if content_block.get('type') == 'text':
          content = content_block.get('text', '')

      if data.get('stop_reason') == 'refusal':
        logger.warning("Claude refused to generate content for safety reasons")
        content += REFUSAL_NOTE

      response_text = content if content else "No response generated"
      yield response_text
      return response_text

    except Exception as e:
      logger.error(f"Error in non-streaming response: {e}")
      error_msg = f"API error: {str(e)}"
      yield error_msg
      return error_msg
