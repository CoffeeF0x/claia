"""
Anthropic API model implementation.

This module provides the AnthropicModel class for interacting with Anthropic's Claude API,
including support for streaming and non-streaming responses.
"""

import json
import logging
from typing import Dict, Any, Optional, Generator

# Internal dependencies
from ...data.chunks import BaseChunk
from ...data.models.conversation.message_sequence import MessageSequence
from ...data.response import ModelResponse
from ...decorators import architecture
from ...enums.conversation import MessageRole
from ...plugins.base import (
  COMMON_TEXT_RUNTIME_PARAMS,
  ParamScope,
  ParamSpec,
  SettingCategory,
)
from ..base import APIModel
from ..base.base import ModelInputs



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
@architecture
@architecture.name("anthropic")
@architecture.title("Anthropic API Architecture")
@architecture.description("Implements Anthropic Claude API-backed models")
@architecture.param(ParamSpec(
  name="anthropic_api_token",
  type=str,
  scope=ParamScope.INIT,
  required=True,
  secret=True,
  category=SettingCategory.API,
  description="Anthropic API Token",
))
@architecture.param(*COMMON_TEXT_RUNTIME_PARAMS)
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

  def generate(
    self,
    inputs: ModelInputs,
    **kwargs,
  ) -> Generator[BaseChunk, None, ModelResponse]:
    """Generate a response using Anthropic's API."""
    chunks: list = []
    try:
      if not isinstance(inputs, MessageSequence):
        raise TypeError("AnthropicModel expects a MessageSequence input")
      system_message, messages = self._convert_sequence(inputs)

      request_data = {
        "model": self.model_name,
        "messages": messages,
        "max_tokens": kwargs.get("max_tokens", 1000),
      }

      if system_message:
        request_data["system"] = system_message

      # Anthropic rejects requests that include both temperature and top_p.
      # Prefer temperature; only send top_p when temperature is absent.
      temperature = kwargs.get("temperature")
      top_p = kwargs.get("top_p")
      top_k = kwargs.get("top_k")

      if temperature is not None:
        request_data["temperature"] = temperature
      elif top_p is not None:
        request_data["top_p"] = top_p

      if top_k is not None:
        request_data["top_k"] = top_k

      if kwargs.get("stream", False):
        request_data["stream"] = True
        token_gen = self._handle_streaming_response(request_data)
      else:
        token_gen = self._handle_non_streaming_response(request_data)

      from ...data.chunks import TextChunk
      try:
        while True:
          token = next(token_gen)
          chunk = TextChunk(data=token) if isinstance(token, str) else token
          chunks.append(chunk)
          yield chunk
      except StopIteration as stop:
        return ModelResponse(
          chunks=chunks,
          complete=True,
          metadata={"text": stop.value},
        )

    except Exception as e:
      logger.error(f"Error generating response with Anthropic model {self.model_name}: {e}")
      from ...data.chunks import TextChunk
      chunk = TextChunk(data=f"Error: {str(e)}")
      chunks.append(chunk)
      yield chunk
      return ModelResponse(chunks=chunks, complete=False, error=str(e))

  def _convert_sequence(self, sequence: MessageSequence) -> tuple:
    """Convert a MessageSequence to Anthropic messages format."""
    messages = []
    for message in sequence.messages:
      if message.speaker == MessageRole.USER and message.content:
        messages.append({"role": "user", "content": message.content})
      elif message.speaker == MessageRole.ASSISTANT and message.content:
        messages.append({"role": "assistant", "content": message.content})
    return sequence.system or "", messages

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
