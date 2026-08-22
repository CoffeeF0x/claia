"""
OpenAI API architecture.

Uses the Responses API (POST /v1/responses).
"""

import logging
from typing import Any, Dict, Generator, List, Optional

from .wire import iter_sse, provider_error
from ...data.chunks import BaseChunk, TextChunk
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
from ...results import DeploymentError
from ..base import APIArchitecture
from ..base.base import ModelInputs


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                               CLASSES                                #
########################################################################
@architecture
@architecture.name("openai")
@architecture.title("OpenAI API Architecture")
@architecture.description("Implements OpenAI chat/completions API-backed models")
@architecture.param(ParamSpec(
  name="openai_api_token",
  type=str,
  scope=ParamScope.INIT,
  required=True,
  secret=True,
  category=SettingCategory.API,
  description="OpenAI API Token",
))
@architecture.param(*COMMON_TEXT_RUNTIME_PARAMS)
class OpenAIArchitecture(APIArchitecture):
  """OpenAI API architecture using the Responses API."""

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
    if not isinstance(inputs, MessageSequence):
      raise TypeError("OpenAIArchitecture expects a MessageSequence input")
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
      return (yield from self._generate_streaming(request_data))
    return (yield from self._generate_blocking(request_data))

  def _convert_sequence(self, sequence: MessageSequence) -> tuple:
    """Convert a MessageSequence to (instructions, input_messages)."""
    instructions = sequence.system
    input_messages: List[Dict[str, str]] = []
    for message in sequence.messages:
      if message.role not in (MessageRole.USER, MessageRole.ASSISTANT):
        continue
      if not message.content:
        continue
      role = "user" if message.role == MessageRole.USER else "assistant"
      input_messages.append({"role": role, "content": message.content})
    return instructions, input_messages

  def _generate_streaming(self, request_data: Dict[str, Any]) -> Generator[BaseChunk, None, ModelResponse]:
    response = self.post("responses", {**request_data, "stream": True}, stream=True)
    chunks: List[BaseChunk] = []
    usage = None

    for event in iter_sse(response):
      event_type = event.get("type")

      if event_type == "response.output_text.delta":
        delta = event.get("delta", "")
        if delta:
          chunk = TextChunk(data=delta)
          chunks.append(chunk)
          yield chunk

      elif event_type in ("error", "response.failed"):
        err = event.get("error") or event.get("response", {}).get("error") or {}
        message = provider_error("OpenAI", err, "unknown error from the Responses API")
        logger.error(message)
        if not chunks:
          raise DeploymentError(message)
        return ModelResponse(chunks=chunks, complete=False, error=message)

      elif event_type in ("response.completed", "response.incomplete"):
        usage = (event.get("response") or {}).get("usage")
        break

    return ModelResponse(
      chunks=chunks,
      complete=True,
      metadata={"usage": usage} if usage else {},
    )

  def _generate_blocking(self, request_data: Dict[str, Any]) -> Generator[BaseChunk, None, ModelResponse]:
    response = self.post("responses", request_data)
    data = response.json()

    err = data.get("error") or (
      data.get("response", {}).get("error") if data.get("status") == "failed" else None
    )
    if err:
      message = provider_error("OpenAI", err, "unknown error from the Responses API")
      logger.error(message)
      raise DeploymentError(message)

    content = ""
    for item in data.get("output", []):
      if item.get("type") == "message":
        for part in item.get("content", []):
          if part.get("type") == "output_text":
            content += part.get("text", "")

    chunk = TextChunk(data=content)
    yield chunk

    usage = data.get("usage")
    return ModelResponse(
      chunks=[chunk],
      complete=True,
      metadata={"usage": usage} if usage else {},
    )
