"""
Anthropic API architecture.

Uses the Messages API (POST /v1/messages), streaming or blocking.
"""

import logging
from typing import Any, Dict, Generator, List, Optional

from .wire import iter_sse, provider_error
from ...data.chunks import BaseChunk, TextChunk
from ...data.models.conversation.message_sequence import MessageSequence
from ...data.response import ModelResponse
from ...decorators import architecture
from ...enums.plugins import ParamScope, ParamCategory
from ...plugins.base import (
  COMMON_TEXT_RUNTIME_PARAMS,
  ParamSpec,
)
from ...results import DeploymentError
from ..base import APIArchitecture
from ..base.base import ModelInputs


########################################################################
#                              CONSTANTS                               #
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
  category=ParamCategory.API,
  description="Anthropic API Token",
))
@architecture.param(*COMMON_TEXT_RUNTIME_PARAMS)
class AnthropicArchitecture(APIArchitecture):
  """Anthropic Claude API architecture."""

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
    """Generate a response using Anthropic's Messages API."""
    if not isinstance(inputs, MessageSequence):
      raise TypeError("AnthropicArchitecture expects a MessageSequence input")
    system_message, messages = self._convert_sequence(inputs)

    request_data: Dict[str, Any] = {
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
      return (yield from self._generate_streaming(request_data))
    return (yield from self._generate_blocking(request_data))

  def _convert_sequence(self, sequence: MessageSequence) -> tuple:
    """Convert a MessageSequence to Anthropic messages format."""
    return sequence.system or "", self.coalesce_consecutive_roles(
      self.format_messages(sequence)
    )

  def _generate_streaming(self, request_data: Dict[str, Any]) -> Generator[BaseChunk, None, ModelResponse]:
    response = self.post("messages", {**request_data, "stream": True}, stream=True)
    chunks: List[BaseChunk] = []
    usage: Dict[str, Any] = {}
    stop_reason = None

    for event in iter_sse(response):
      event_type = event.get("type")

      if event_type == "content_block_delta":
        delta = event.get("delta", {})
        if delta.get("type") == "text_delta" and delta.get("text"):
          chunk = TextChunk(data=delta["text"])
          chunks.append(chunk)
          yield chunk

      elif event_type == "message_start":
        usage.update((event.get("message") or {}).get("usage") or {})

      elif event_type == "message_delta":
        usage.update(event.get("usage") or {})
        delta = event.get("delta", {})
        if "stop_reason" in delta:
          stop_reason = delta["stop_reason"]

      elif event_type == "error":
        message = provider_error("Anthropic", event.get("error"), "unknown error from the Messages API")
        logger.error(message)
        if not chunks:
          raise DeploymentError(message)
        return ModelResponse(chunks=chunks, complete=False, error=message)

    if stop_reason == "refusal":
      logger.warning("Claude refused to generate content for safety reasons")
      chunk = TextChunk(data=REFUSAL_NOTE)
      chunks.append(chunk)
      yield chunk

    return ModelResponse(
      chunks=chunks,
      complete=True,
      metadata={"usage": usage} if usage else {},
    )

  def _generate_blocking(self, request_data: Dict[str, Any]) -> Generator[BaseChunk, None, ModelResponse]:
    response = self.post("messages", request_data)
    data = response.json()

    if data.get("type") == "error":
      message = provider_error("Anthropic", data.get("error"), "unknown error from the Messages API")
      logger.error(message)
      raise DeploymentError(message)

    content = ""
    if data.get("content"):
      content_block = data["content"][0]
      if content_block.get("type") == "text":
        content = content_block.get("text", "")

    if data.get("stop_reason") == "refusal":
      logger.warning("Claude refused to generate content for safety reasons")
      content += REFUSAL_NOTE

    chunk = TextChunk(data=content)
    yield chunk

    usage = data.get("usage")
    return ModelResponse(
      chunks=[chunk],
      complete=True,
      metadata={"usage": usage} if usage else {},
    )
