"""
OpenAI API model implementation.

Uses the Responses API (POST /v1/responses), which is the recommended
endpoint for all current OpenAI models and the only endpoint that
supports GPT-5.x reasoning, built-in tools, and prompt caching.

Key differences from the old Chat Completions endpoint:
  - Endpoint:   v1/responses  (was v1/chat/completions)
  - Input key:  input         (was messages)
  - System msg: instructions  (top-level field, not a system-role message)
  - Max tokens: max_output_tokens  (was max_tokens)
  - Response:   output[].content[].text  (was choices[0].message.content)
  - Streaming:  event type response.output_text.delta  (was choices[0].delta.content)
"""

import json
import logging
from typing import Dict, Any, Optional, Generator

# Internal dependencies
from claia.core.data.chunks import BaseChunk, TextChunk
from claia.core.data.models.conversation.message_sequence import MessageSequence
from claia.core.data.response import ModelResponse
from ..base import APIModel


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
    sequence: MessageSequence,
    **kwargs,
  ) -> Generator[BaseChunk, None, ModelResponse]:
    """Generate a response using OpenAI's Responses API.

    Yields ``TextChunk`` tokens; returns a ``ModelResponse``.
    """
    chunks = []
    try:
      instructions, input_messages = self._convert_sequence(sequence)

      # Build base request — excluded fields are handled explicitly below.
      # n, stop, and top_k are Chat Completions params not supported by the
      # Responses API; including them causes a 400 Bad Request.
      _skip = {"stream", "max_tokens", "n", "stop", "top_k"}
      request_data: Dict[str, Any] = {
        "model": self.model_name,
        "input": input_messages,
        "store": False,
        **{k: v for k, v in kwargs.items() if v is not None and k not in _skip},
      }

      if instructions:
        request_data["instructions"] = instructions

      # Responses API uses max_output_tokens instead of max_tokens
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
    """Convert a MessageSequence to (instructions, input_messages).

    The system prompt becomes the top-level `instructions` field.
    Only user and assistant turns are included in `input`.
    """
    return sequence.system, sequence.to_chat_dicts(include_system=False)

  def _handle_streaming_response(self, request_data: Dict[str, Any]) -> Generator[str, None, str]:
    """Handle streaming response from the Responses API. Yields tokens, returns full response.

    The Responses API SSE stream emits typed events. Text deltas arrive as
    events with type == "response.output_text.delta" and a "delta" string field.

    The stream can also terminate with non-delta events that the caller needs
    to know about:
      - "error" / "response.failed": API returned 200 but the run failed
        partway through (e.g. quota, content filter). These carry a nested
        ``error.message`` that we surface so it reaches the user.
      - "response.completed": clean end of stream; no [DONE] sentinel is sent.
    Without explicit handling these events were silently dropped, leaving
    the CLI with a long pause and an empty assistant message.
    """
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
    """Handle non-streaming response from the Responses API. Yields full content as single token.

    The response body has an `output` array of items. Text lives in items
    where type == "message", under content parts where type == "output_text".
    """
    try:
      response = self.post("responses", request_data)
      data = response.json()

      # Non-streaming runs can still report a failure inline via top-level
      # error or response.status == "failed" with a nested error block.
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
