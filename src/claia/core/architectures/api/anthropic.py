"""
Anthropic API architecture.

Uses the Messages API (POST /v1/messages), streaming or blocking.
"""

import logging
from typing import Any, Dict, Generator, List, Optional

from .tools import TOOLS_PARAM, anthropic_tools, format_anthropic_messages, tool_chunk
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
@architecture.param(TOOLS_PARAM)
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
    tools = kwargs.pop("tools", None)
    system_message, messages = self._convert_sequence(inputs, native=bool(tools))

    request_data: Dict[str, Any] = {
      "model": self.model_name,
      "messages": messages,
      "max_tokens": kwargs.get("max_tokens", 1000),
    }
    if tools:
      request_data["tools"] = anthropic_tools(tools)

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

  def _convert_sequence(self, sequence: MessageSequence, native: bool = False) -> tuple:
    """Convert a MessageSequence to Anthropic messages format."""
    if native:
      return sequence.system or "", format_anthropic_messages(sequence)
    return sequence.system or "", self.coalesce_consecutive_roles(
      self.format_messages(sequence)
    )

  def _generate_streaming(self, request_data: Dict[str, Any]) -> Generator[BaseChunk, None, ModelResponse]:
    response = self.post("messages", {**request_data, "stream": True}, stream=True)
    chunks: List[BaseChunk] = []
    usage: Dict[str, Any] = {}
    stop_reason = None
    tool_blocks: Dict[int, Dict[str, str]] = {}

    for event in iter_sse(response):
      event_type = event.get("type")

      if event_type == "content_block_start":
        block = event.get("content_block") or {}
        if block.get("type") == "tool_use":
          tool_blocks[event.get("index", 0)] = {
            "id": block.get("id") or "",
            "name": block.get("name") or "",
            "json": "",
          }

      elif event_type == "content_block_delta":
        delta = event.get("delta", {})
        if delta.get("type") == "text_delta" and delta.get("text"):
          chunk = TextChunk(data=delta["text"])
          chunks.append(chunk)
          yield chunk
        elif delta.get("type") == "input_json_delta":
          slot = tool_blocks.get(event.get("index", 0))
          if slot is not None:
            slot["json"] += delta.get("partial_json") or ""

      elif event_type == "content_block_stop":
        slot = tool_blocks.pop(event.get("index", 0), None)
        if slot is not None:
          chunk = tool_chunk(slot["name"], slot["json"], slot["id"] or None)
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
    tool_chunks: List[BaseChunk] = []
    for block in data.get("content") or []:
      if block.get("type") == "text":
        content += block.get("text", "")
      elif block.get("type") == "tool_use":
        tool_chunks.append(tool_chunk(
          block.get("name"),
          block.get("input"),
          block.get("id"),
        ))

    if data.get("stop_reason") == "refusal":
      logger.warning("Claude refused to generate content for safety reasons")
      content += REFUSAL_NOTE

    chunks: List[BaseChunk] = []
    if content or not tool_chunks:
      chunk = TextChunk(data=content)
      chunks.append(chunk)
      yield chunk
    for chunk in tool_chunks:
      chunks.append(chunk)
      yield chunk

    usage = data.get("usage")
    return ModelResponse(
      chunks=chunks,
      complete=True,
      metadata={"usage": usage} if usage else {},
    )
