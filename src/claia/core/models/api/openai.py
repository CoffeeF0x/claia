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
  """OpenAI API model implementation using the Responses API."""

  def __init__(self, model_name: str, openai_api_token: Optional[str] = None):
    super().__init__(model_name, "https://api.openai.com/v1")
    if openai_api_token:
      self.set_api_key(openai_api_token)

  def generate(self, conversation: Conversation, **kwargs) -> Generator[str, None, str]:
    """Generate a response using OpenAI's Responses API. Yields tokens, returns full response."""
    try:
      settings = self.update_settings({}, **kwargs)
      instructions, input_messages = self._convert_conversation(conversation)

      # Build base request — excluded fields are handled explicitly below
      _skip = {"stream", "max_tokens"}
      request_data: Dict[str, Any] = {
        "model": self.model_name,
        "input": input_messages,
        "store": False,
        **{k: v for k, v in settings.items() if v is not None and k not in _skip},
      }

      if instructions:
        request_data["instructions"] = instructions

      # Responses API uses max_output_tokens instead of max_tokens
      max_tokens = settings.get("max_tokens")
      if max_tokens is not None:
        request_data["max_output_tokens"] = max_tokens

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

  def _convert_conversation(self, conversation: Conversation) -> tuple:
    """Convert a Conversation to (instructions, input_messages) for the Responses API.

    The system prompt becomes the top-level `instructions` field.
    Only user and assistant turns are included in `input`.
    """
    instructions = conversation.get_system_prompt() or None

    input_messages = []
    for message in conversation.get_thread():
      if message.speaker not in (MessageRole.USER, MessageRole.ASSISTANT):
        continue
      role = "user" if message.speaker == MessageRole.USER else "assistant"
      input_messages.append({"role": role, "content": message.content})

    return instructions, input_messages

  def _handle_streaming_response(self, request_data: Dict[str, Any]) -> Generator[str, None, str]:
    """Handle streaming response from the Responses API. Yields tokens, returns full response.

    The Responses API SSE stream emits typed events. Text deltas arrive as
    events with type == "response.output_text.delta" and a "delta" string field.
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
          if data.get("type") == "response.output_text.delta":
            delta = data.get("delta", "")
            full_response += delta
            yield delta
        except json.JSONDecodeError:
          continue

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
