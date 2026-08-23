"""
OpenRouter API architecture.

OpenRouter exposes an OpenAI-compatible Chat Completions API across
many providers. The framework-facing contract matches the other API
architectures: ``generate`` yields text deltas when ``stream`` is true
and yields one complete text response otherwise.
"""

import logging
from typing import Any, Dict, Generator, List, Optional

from .tools import TOOLS_PARAM, format_openai_chat_messages, openai_chat_tools, tool_chunk
from .wire import iter_sse, provider_error, usage_chunk
from ...data.chunks import BaseChunk, TextChunk
from ...data.models.conversation.message_sequence import MessageSequence
from ...data.request import AgentRequest
from ...decorators import architecture
from ...enums.plugins import ParamScope, ParamCategory
from ...plugins.base import (
  COMMON_TEXT_RUNTIME_PARAMS,
  ParamSpec,
)
from ...results import DeploymentError
from ..base import APIArchitecture


########################################################################
#                              CONSTANTS                               #
########################################################################
DEFAULT_HTTP_REFERER = "http://localhost:3000"
DEFAULT_X_TITLE = "CLAIA"

PASSTHROUGH_PARAMS = (
  "max_tokens",
  "temperature",
  "top_p",
  "top_k",
  "presence_penalty",
  "frequency_penalty",
  "stop",
  "n",
)


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                               CLASSES                                #
########################################################################
@architecture
@architecture.name("openrouter")
@architecture.title("OpenRouter API Architecture")
@architecture.description("Implements OpenRouter's OpenAI-compatible chat completions API")
@architecture.param(ParamSpec(
  name="openrouter_api_token",
  type=str,
  scope=ParamScope.INIT,
  secret=True,
  category=ParamCategory.API,
  description="OpenRouter API Token",
))
@architecture.param(ParamSpec(
  name="openrouter_http_referer",
  type=str,
  scope=ParamScope.INIT,
  default="http://localhost:3000",
  category=ParamCategory.ENDPOINT,
  description="HTTP-Referer header sent to OpenRouter for app attribution.",
))
@architecture.param(ParamSpec(
  name="openrouter_x_title",
  type=str,
  scope=ParamScope.INIT,
  default="CLAIA",
  category=ParamCategory.APPLICATION,
  description="X-Title header sent to OpenRouter for app attribution.",
))
@architecture.param(TOOLS_PARAM)
@architecture.param(*COMMON_TEXT_RUNTIME_PARAMS)
class OpenRouterArchitecture(APIArchitecture):
  """OpenRouter API architecture."""

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

  def _format_messages(self, sequence: MessageSequence, native: bool = False) -> List[Dict[str, Any]]:
    """Format a message sequence for the OpenRouter API."""
    messages: List[Dict[str, Any]] = []
    if sequence.system:
      messages.append({"role": "system", "content": sequence.system})
    if native:
      messages.extend(format_openai_chat_messages(sequence))
    else:
      messages.extend(self.format_messages(sequence))
    logger.debug(f"Sending {len(messages)} messages to OpenRouter API")
    return messages

  def generate(
    self,
    request: AgentRequest,
  ) -> Generator[BaseChunk, None, None]:
    """Generate a response using the OpenRouter API."""
    inputs = request.inputs
    args = request.args
    if not isinstance(inputs, MessageSequence):
      raise TypeError("OpenRouterArchitecture expects a MessageSequence input")
    tools = args.get("tools")

    request_data: Dict[str, Any] = {
      "model": self.model_name,
      "messages": self._format_messages(inputs, native=bool(tools)),
    }
    for param in PASSTHROUGH_PARAMS:
      value = args.get(param)
      if value is not None:
        request_data[param] = value
    if tools:
      request_data["tools"] = openai_chat_tools(tools)

    if args.get("stream", False):
      return (yield from self._generate_streaming(request_data, tools=tools))
    return (yield from self._generate_blocking(request_data, tools=tools))

  def _generate_streaming(self, request_data: Dict[str, Any], tools=None) -> Generator[BaseChunk, None, None]:
    payload = {**request_data, "stream": True, "stream_options": {"include_usage": True}}
    response = self.post("chat/completions", payload, stream=True)
    pending: Dict[int, Dict[str, str]] = {}
    usage = None
    finish_reason = None

    for event in iter_sse(response):
      if "error" in event:
        message = provider_error("OpenRouter", event.get("error"), "unknown error from the OpenRouter API")
        logger.error(message)
        raise DeploymentError(message)

      if event.get("usage"):
        usage = event["usage"]

      choices = event.get("choices") or []
      if not choices:
        continue

      finish_reason = choices[0].get("finish_reason") or finish_reason
      delta = choices[0].get("delta") or {}
      content = delta.get("content")
      if content:
        yield TextChunk(data=content)

      for call in delta.get("tool_calls") or []:
        idx = call.get("index", 0)
        slot = pending.setdefault(idx, {"id": "", "name": "", "arguments": ""})
        if call.get("id"):
          slot["id"] = call["id"]
        function = call.get("function") or {}
        if function.get("name"):
          slot["name"] += function["name"]
        if function.get("arguments"):
          slot["arguments"] += function["arguments"]

    for slot in pending.values():
      if not slot["name"]:
        continue
      yield tool_chunk(slot["name"], slot["arguments"], slot["id"] or None, tools=tools)

    chunk = usage_chunk(
      usage, provider="openrouter", provider_model=self.model_name, finish_reason=finish_reason,
    )
    if chunk:
      yield chunk

  def _generate_blocking(self, request_data: Dict[str, Any], tools=None) -> Generator[BaseChunk, None, None]:
    response = self.post("chat/completions", request_data)
    data = response.json()

    if "error" in data:
      message = provider_error("OpenRouter", data.get("error"), "unknown error from the OpenRouter API")
      logger.error(message)
      raise DeploymentError(message)

    choices = data.get("choices") or []
    if not choices:
      logger.error(f"Unexpected response format from OpenRouter: {data}")
      raise DeploymentError("OpenRouter error: invalid response format")

    message = choices[0].get("message") or {}
    content = message.get("content") or ""
    tool_chunks = [
      tool_chunk(
        (call.get("function") or {}).get("name"),
        (call.get("function") or {}).get("arguments"),
        call.get("id"),
        tools=tools,
      )
      for call in message.get("tool_calls") or []
      if (call.get("function") or {}).get("name")
    ]

    if content or not tool_chunks:
      yield TextChunk(data=content)
    for chunk in tool_chunks:
      yield chunk

    chunk = usage_chunk(
      data.get("usage"),
      provider="openrouter",
      provider_model=self.model_name,
      finish_reason=choices[0].get("finish_reason"),
    )
    if chunk:
      yield chunk
