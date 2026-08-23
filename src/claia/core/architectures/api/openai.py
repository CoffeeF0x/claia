"""
OpenAI API architecture.

Uses the Responses API (POST /v1/responses).
"""

import logging
from typing import Any, Dict, Generator, List, Optional

from .tools import (
  TOOLS_PARAM,
  format_openai_responses_input,
  openai_responses_tools,
  tool_chunk,
)
from .wire import iter_sse, provider_error
from ...data.chunks import BaseChunk, TextChunk
from ...data.models.conversation.message_sequence import MessageSequence
from ...data.request import AgentRequest
from ...data.response import ModelResponse
from ...decorators import architecture
from ...enums.plugins import ParamScope, ParamCategory
from ...plugins.base import (
  COMMON_TEXT_RUNTIME_PARAMS,
  ParamSpec,
)
from ...results import DeploymentError
from ..base import APIArchitecture


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
@architecture.description("Implements OpenAI Responses API-backed models")
@architecture.param(ParamSpec(
  name="openai_api_token",
  type=str,
  scope=ParamScope.INIT,
  required=True,
  secret=True,
  category=ParamCategory.API,
  description="OpenAI API Token",
))
@architecture.param(TOOLS_PARAM)
@architecture.param(*COMMON_TEXT_RUNTIME_PARAMS)
class OpenAIArchitecture(APIArchitecture):
  """OpenAI API architecture using the Responses API."""

  def __init__(self, model_name: str, openai_api_token: Optional[str] = None):
    super().__init__(model_name, "https://api.openai.com/v1")
    if openai_api_token:
      self.set_api_key(openai_api_token)

  def generate(
    self,
    request: AgentRequest,
  ) -> Generator[BaseChunk, None, ModelResponse]:
    """Generate a response using OpenAI's Responses API."""
    inputs = request.inputs
    args = request.args
    if not isinstance(inputs, MessageSequence):
      raise TypeError("OpenAIArchitecture expects a MessageSequence input")
    tools = args.get("tools")
    instructions, input_messages = self._convert_sequence(inputs, native=bool(tools))

    _skip = {"stream", "max_tokens", "n", "stop", "top_k", "tools"}
    request_data: Dict[str, Any] = {
      "model": self.model_name,
      "input": input_messages,
      "store": False,
      **{k: v for k, v in args.items() if v is not None and k not in _skip},
    }
    if tools:
      request_data["tools"] = openai_responses_tools(tools)

    if instructions:
      request_data["instructions"] = instructions

    max_tokens = args.get("max_tokens")
    if max_tokens is not None:
      request_data["max_output_tokens"] = max_tokens

    if args.get("stream", False):
      return (yield from self._generate_streaming(request_data, tools=tools))
    return (yield from self._generate_blocking(request_data, tools=tools))

  def _convert_sequence(self, sequence: MessageSequence, native: bool = False) -> tuple:
    """Convert a MessageSequence to (instructions, input_messages)."""
    if native:
      return sequence.system, format_openai_responses_input(sequence)
    return sequence.system, self.format_messages(sequence)

  def _generate_streaming(self, request_data: Dict[str, Any], tools=None) -> Generator[BaseChunk, None, ModelResponse]:
    response = self.post("responses", {**request_data, "stream": True}, stream=True)
    chunks: List[BaseChunk] = []
    emitted: set = set()
    usage = None

    def emit_function_call(item: Dict[str, Any]) -> Generator[BaseChunk, None, None]:
      if item.get("type") != "function_call":
        return
      key = item.get("call_id") or item.get("id")
      if key in emitted:
        return
      chunk = tool_chunk(item.get("name"), item.get("arguments"), item.get("call_id") or item.get("id"), tools=tools)
      if key:
        emitted.add(key)
      chunks.append(chunk)
      yield chunk

    for event in iter_sse(response):
      event_type = event.get("type")

      if event_type == "response.output_text.delta":
        delta = event.get("delta", "")
        if delta:
          chunk = TextChunk(data=delta)
          chunks.append(chunk)
          yield chunk

      elif event_type == "response.output_item.done":
        yield from emit_function_call(event.get("item") or {})

      elif event_type in ("error", "response.failed"):
        err = event.get("error") or event.get("response", {}).get("error") or {}
        message = provider_error("OpenAI", err, "unknown error from the Responses API")
        logger.error(message)
        if not chunks:
          raise DeploymentError(message)
        return ModelResponse(chunks=chunks, complete=False, error=message)

      elif event_type in ("response.completed", "response.incomplete"):
        payload = event.get("response") or {}
        usage = payload.get("usage")
        for item in payload.get("output") or []:
          yield from emit_function_call(item)
        break

    return ModelResponse(
      chunks=chunks,
      complete=True,
      metadata={"usage": usage} if usage else {},
    )

  def _generate_blocking(self, request_data: Dict[str, Any], tools=None) -> Generator[BaseChunk, None, ModelResponse]:
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
    tool_chunks: List[BaseChunk] = []
    for item in data.get("output", []):
      if item.get("type") == "message":
        for part in item.get("content", []):
          if part.get("type") == "output_text":
            content += part.get("text", "")
      elif item.get("type") == "function_call":
        tool_chunks.append(tool_chunk(
          item.get("name"),
          item.get("arguments"),
          item.get("call_id") or item.get("id"),
          tools=tools,
        ))

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
