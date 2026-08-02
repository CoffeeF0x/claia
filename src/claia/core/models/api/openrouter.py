"""
OpenRouter API model implementation.

OpenRouter exposes an OpenAI-compatible Chat Completions API across many
providers. This module keeps the framework-facing contract the same as
the other API models: ``generate`` yields text deltas when ``stream`` is
true and yields one complete text response otherwise.
"""

import json
import logging
from typing import Any, Dict, Generator, List, Optional

# Internal dependencies
from ..base import APIModel
from claia.core.data.chunks import BaseChunk, TextChunk
from claia.core.data.models.conversation.message_sequence import MessageSequence
from claia.core.data.response import ModelResponse


########################################################################
#                              CONSTANTS                               #
########################################################################
DEFAULT_HTTP_REFERER = "http://localhost:3000"
DEFAULT_X_TITLE = "CLAIA"


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                               CLASSES                                #
########################################################################
class OpenRouterModel(APIModel):
  """OpenRouter API model implementation."""

  def __init__(
    self,
    model_name: str,
    openrouter_api_token: Optional[str] = None,
    openrouter_http_referer: str = DEFAULT_HTTP_REFERER,
    openrouter_x_title: str = DEFAULT_X_TITLE,
  ):
    super().__init__(model_name, base_url="https://openrouter.ai/api/v1")
    self.set_custom_header("HTTP-Referer", openrouter_http_referer)
    self.set_custom_header("X-Title", openrouter_x_title)
    if openrouter_api_token:
      self.set_api_key(openrouter_api_token)

  def _format_messages(self, sequence: MessageSequence) -> List[Dict[str, Any]]:
    """Format a message sequence for the OpenRouter API."""
    messages = sequence.to_chat_dicts(include_system=True)
    logger.debug(f"Sending {len(messages)} messages to OpenRouter API")
    return messages

  def generate(
    self,
    sequence: MessageSequence,
    **kwargs,
  ) -> Generator[BaseChunk, None, ModelResponse]:
    """Generate a response using the OpenRouter API."""
    chunks: list = []
    try:
      request_data = {
        "model": self.model_name,
        "messages": self._format_messages(sequence),
      }

      for param in (
        "max_tokens",
        "temperature",
        "top_p",
        "top_k",
        "presence_penalty",
        "frequency_penalty",
        "stop",
        "n",
      ):
        value = kwargs.get(param)
        if value is not None:
          request_data[param] = value

      if kwargs.get("stream", False):
        token_gen = self._handle_streaming_response(request_data)
      else:
        token_gen = self._handle_non_streaming_response(request_data)

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
      logger.error(f"Error generating response with OpenRouter model {self.model_name}: {e}")
      chunk = TextChunk(data=f"Error: {str(e)}")
      chunks.append(chunk)
      yield chunk
      return ModelResponse(chunks=chunks, complete=False, error=str(e))

  def _extract_error_message(self, data: Dict[str, Any], fallback: str) -> str:
    """Extract OpenRouter error details from an API response body."""
    err = data.get("error")
    if isinstance(err, dict):
      message = err.get("message") or fallback
      code = err.get("code") or err.get("type")
      return f"OpenRouter error ({code}): {message}" if code else f"OpenRouter error: {message}"
    if isinstance(err, str):
      return f"OpenRouter error: {err}"
    return fallback

  def _handle_streaming_response(self, request_data: Dict[str, Any]) -> Generator[str, None, str]:
    """Stream response from the OpenRouter API. Yields tokens, returns full response."""
    try:
      response = self.post("chat/completions", {**request_data, "stream": True}, stream=True)
      full_response = ""

      for line in response.iter_lines():
        if not line:
          continue

        line_text = line.decode("utf-8") if isinstance(line, bytes) else line
        if not line_text.startswith("data: "):
          continue

        data_line = line_text[6:]
        if data_line.strip() == "[DONE]":
          break

        try:
          chunk = json.loads(data_line)
        except json.JSONDecodeError:
          logger.warning(f"Failed to parse streaming response: {data_line}")
          continue

        if "error" in chunk:
          error_msg = self._extract_error_message(chunk, "Unknown error from OpenRouter API")
          logger.error(error_msg)
          yield error_msg
          return error_msg

        choices = chunk.get("choices") or []
        if not choices:
          continue

        delta = choices[0].get("delta") or {}
        content_chunk = delta.get("content")
        if content_chunk:
          full_response += content_chunk
          yield content_chunk

      return full_response

    except Exception as e:
      logger.error(f"Error in streaming response: {e}")
      error_msg = f"Streaming error: {str(e)}"
      yield error_msg
      return error_msg

  def _handle_non_streaming_response(self, request_data: Dict[str, Any]) -> Generator[str, None, str]:
    """Get non-streaming response from the OpenRouter API. Yields full content as single token."""
    try:
      response = self.post("chat/completions", request_data)
      data = response.json()

      if "error" in data:
        error_msg = self._extract_error_message(data, "Unknown error from OpenRouter API")
        logger.error(error_msg)
        yield error_msg
        return error_msg

      choices = data.get("choices") or []
      if choices:
        response_text = choices[0].get("message", {}).get("content", "")
        response_text = response_text if response_text else "No response generated"
        yield response_text
        return response_text

      logger.error(f"Unexpected response format from OpenRouter: {data}")
      error_msg = "Error: Invalid response from OpenRouter API"
      yield error_msg
      return error_msg

    except Exception as e:
      logger.error(f"Error in non-streaming response: {e}")
      error_msg = f"API error: {str(e)}"
      yield error_msg
      return error_msg
