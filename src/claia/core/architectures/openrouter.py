"""
OpenRouter architecture plugin.

Provides OpenAI-compatible chat completions through OpenRouter.
"""

import logging
from typing import Type

from .base import BaseArchitecture
from ..decorators import architecture
from ..models.api import OpenRouterModel
from ..plugins.base import (
  COMMON_TEXT_RUNTIME_PARAMS,
  ParamScope,
  ParamSpec,
  SettingCategory,
)


logger = logging.getLogger(__name__)


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
class OpenRouterPlugin(BaseArchitecture):
  """OpenRouter architecture plugin providing routed API models."""

  def get_model_class(self) -> Type:
    logger.debug("Providing OpenRouterModel class for OpenRouter architecture")
    return OpenRouterModel
