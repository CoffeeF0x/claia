"""
OpenRouter API architecture.

OpenRouter exposes an OpenAI-compatible Chat Completions API across
many providers. The framework-facing contract matches the other API
architectures: ``generate`` yields text deltas when ``stream`` is true
and yields one complete text response otherwise.
"""

import logging
from typing import Any, Dict, Generator, List, Optional

from .wire import iter_sse, provider_error
from ...data.chunks import BaseChunk, TextChunk
from ...data.models.conversation.message_sequence import MessageSequence
from ...data.response import ModelResponse
from ...decorators import architecture
from ...enums.conversation import MessageRole
from ...enums.plugins import ParamScope, SettingCategory
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
  category=SettingCategory.API,
  description="OpenRouter API Token",
))
@architecture.param(ParamSpec(
  name="openrouter_http_referer",
  type=str,
  scope=ParamScope.INIT,
  default="http://localhost:3000",
  category=SettingCategory.ENDPOINT,
  description="HTTP-Referer header sent to OpenRouter for app attribution.",
))
@architecture.param(ParamSpec(
  name="openrouter_x_title",
  type=str,
  scope=ParamScope.INIT,
  default="CLAIA",
  category=SettingCategory.APPLICATION,
  description="X-Title header sent to OpenRouter for app attribution.",
))
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

  def _format_messages(self, sequence: MessageSequence) -> List[Dict[str, Any]]:
    """Format a message sequence for the OpenRouter API."""
    messages: List[Dict[str, Any]] = []
    if sequence.system:
      messages.append({"role": "system", "content": sequence.system})
    for message in sequence.messages:
      if message.role not in (MessageRole.USER, MessageRole.ASSISTANT):
        continue
      if not message.content:
        continue
      messages.append({
        "role": message.role.value,
        "content": message.content,
      })
    logger.debug(f"Sending {len(messages)} messages to OpenRouter API")
    return messages

  def generate(
    self,
    inputs: ModelInputs,
    **kwargs,
  ) -> Generator[BaseChunk, None, ModelResponse]:
    """Generate a response using the OpenRouter API."""
    if not isinstance(inputs, MessageSequence):
      raise TypeError("OpenRouterArchitecture expects a MessageSequence input")

    request_data: Dict[str, Any] = {
      "model": self.model_name,
      "messages": self._format_messages(inputs),
    }
    for param in PASSTHROUGH_PARAMS:
      value = kwargs.get(param)
      if value is not None:
        request_data[param] = value

    if kwargs.get("stream", False):
      return (yield from self._generate_streaming(request_data))
    return (yield from self._generate_blocking(request_data))

  def _generate_streaming(self, request_data: Dict[str, Any]) -> Generator[BaseChunk, None, ModelResponse]:
    response = self.post("chat/completions", {**request_data, "stream": True}, stream=True)
    chunks: List[BaseChunk] = []
    usage = None

    for event in iter_sse(response):
      if "error" in event:
        message = provider_error("OpenRouter", event.get("error"), "unknown error from the OpenRouter API")
        logger.error(message)
        if not chunks:
          raise DeploymentError(message)
        return ModelResponse(chunks=chunks, complete=False, error=message)

      if event.get("usage"):
        usage = event["usage"]

      choices = event.get("choices") or []
      if not choices:
        continue

      content = (choices[0].get("delta") or {}).get("content")
      if content:
        chunk = TextChunk(data=content)
        chunks.append(chunk)
        yield chunk

    return ModelResponse(
      chunks=chunks,
      complete=True,
      metadata={"usage": usage} if usage else {},
    )

  def _generate_blocking(self, request_data: Dict[str, Any]) -> Generator[BaseChunk, None, ModelResponse]:
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

    content = choices[0].get("message", {}).get("content", "") or ""
    chunk = TextChunk(data=content)
    yield chunk

    usage = data.get("usage")
    return ModelResponse(
      chunks=[chunk],
      complete=True,
      metadata={"usage": usage} if usage else {},
    )
