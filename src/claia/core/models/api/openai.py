"""
OpenAI API model implementation.

Uses the Responses API (POST /v1/responses).
"""

import json
import logging
from typing import Dict, Any, Optional, Generator, List

from claia.core.data.chunks import BaseChunk, TextChunk
from claia.core.data.models.conversation.message_sequence import MessageSequence
from claia.core.data.response import ModelResponse
from claia.core.enums.conversation import MessageRole
from ..base import APIModel
from ..base.base import ModelInputs


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                               CLASSES                                #
########################################################################
class OpenAIModel(APIModel):
  """OpenAI API model implementation using the Responses API."""

  def __init__(self, model_name: str, openai_api_token: Optional[str] = None):
    super().__init__(model_name, "https://api.openai.com/v1")
    if openai_api_token:
      self.set_api_key(openai_api_token)

  def generate(
    self,
    inputs: ModelInputs,
    **kwargs,
  ) -> Generator[BaseChunk, None, ModelResponse]:
    """Generate a response using OpenAI's Responses API."""
    chunks = []
    try:
      if not isinstance(inputs, MessageSequence):
        raise TypeError("OpenAIModel expects a MessageSequence input")
      instructions, input_messages = self._convert_sequence(inputs)

      _skip = {"stream", "max_tokens", "n", "stop", "top_k"}
      request_data: Dict[str, Any] = {
        "model": self.model_name,
        "input": input_messages,
        "store": False,
        **{k: v for k, v in kwargs.items() if v is not None and k not in _skip},
      }

      if instructions:
        request_data["instructions"] = instructions

      max_tokens = kwargs.get("max_tokens")
      if max_tokens is not None:
        request_data["max_output_tokens"] = max_tokens

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
      logger.error(f"Error generating response with OpenAI model {self.model_name}: {e}")
      chunk = TextChunk(data=f"Error: {str(e)}")
      chunks.append(chunk)
      yield chunk
      return ModelResponse(chunks=chunks, complete=False, error=str(e))

  def _convert_sequence(self, sequence: MessageSequence) -> tuple:
    """Convert a MessageSequence to (instructions, input_messages)."""
    instructions = sequence.system
    input_messages: List[Dict[str, str]] = []
    for message in sequence.messages:
      if message.speaker not in (MessageRole.USER, MessageRole.ASSISTANT):
        continue
      if not message.content:
        continue
      role = "user" if message.speaker == MessageRole.USER else "assistant"
      input_messages.append({"role": role, "content": message.content})
    return instructions, input_messages

  def _handle_streaming_response(self, request_data: Dict[str, Any]) -> Generator[str, None, str]:
    try:
      response = self.post("responses", {**request_data, "stream": True}, stream=True)
      full_response = ""

      for line in response.iter_lines():
        if not line:
          continue
        line_text = line.decode("utf-8")

        if not line_text.startswith("data: "):
          continue

        data_text = line_text[6:]
        if data_text.strip() == "[DONE]":
          break

        try:
          data = json.loads(data_text)
        except json.JSONDecodeError:
          continue

        event_type = data.get("type")

        if event_type == "response.output_text.delta":
          delta = data.get("delta", "")
          full_response += delta
          yield delta

        elif event_type in ("error", "response.failed"):
          err = data.get("error") or data.get("response", {}).get("error") or {}
          message = err.get("message") or "Unknown error from OpenAI Responses API"
          code = err.get("code") or err.get("type")
          error_msg = f"OpenAI error ({code}): {message}" if code else f"OpenAI error: {message}"
          logger.error(error_msg)
          yield error_msg
          return error_msg

        elif event_type in ("response.completed", "response.incomplete"):
          break

      return full_response

    except Exception as e:
      logger.error(f"Error in streaming response: {e}")
      error_msg = f"Streaming error: {str(e)}"
      yield error_msg
      return error_msg

  def _handle_non_streaming_response(self, request_data: Dict[str, Any]) -> Generator[str, None, str]:
    try:
      response = self.post("responses", request_data)
      data = response.json()

      err = data.get("error") or (
        data.get("response", {}).get("error") if data.get("status") == "failed" else None
      )
      if err:
        message = err.get("message") or "Unknown error from OpenAI Responses API"
        code = err.get("code") or err.get("type")
        error_msg = f"OpenAI error ({code}): {message}" if code else f"OpenAI error: {message}"
        logger.error(error_msg)
        yield error_msg
        return error_msg

      content = ""
      for item in data.get("output", []):
        if item.get("type") == "message":
          for part in item.get("content", []):
            if part.get("type") == "output_text":
              content += part.get("text", "")

      response_text = content if content else "No response generated"
      yield response_text
      return response_text

    except Exception as e:
      logger.error(f"Error in non-streaming response: {e}")
      error_msg = f"API error: {str(e)}"
      yield error_msg
      return error_msg
