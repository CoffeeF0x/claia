"""
OpenRouter architecture plugin.

Provides OpenAI-compatible chat completions through OpenRouter.
"""

import logging
from typing import Type

from .base import BaseArchitecture
from ..models.api import OpenRouterModel
from ..plugins.base import (
  COMMON_TEXT_RUNTIME_PARAMS,
  ArchitectureInfo,
  ParamScope,
  ParamSpec,
  SettingCategory,
)


logger = logging.getLogger(__name__)


class OpenRouterPlugin(BaseArchitecture):
  """OpenRouter architecture plugin providing routed API models."""

  info = ArchitectureInfo(
    name="openrouter",
    title="OpenRouter API Architecture",
    description="Implements OpenRouter's OpenAI-compatible chat completions API",
    params=[
      ParamSpec(
        name="openrouter_api_token",
        type=str,
        scope=ParamScope.INIT,
        secret=True,
        category=SettingCategory.API,
        description="OpenRouter API Token",
      ),
      ParamSpec(
        name="openrouter_http_referer",
        type=str,
        scope=ParamScope.INIT,
        default="http://localhost:3000",
        category=SettingCategory.ENDPOINT,
        description="HTTP-Referer header sent to OpenRouter for app attribution.",
      ),
      ParamSpec(
        name="openrouter_x_title",
        type=str,
        scope=ParamScope.INIT,
        default="CLAIA",
        category=SettingCategory.APPLICATION,
        description="X-Title header sent to OpenRouter for app attribution.",
      ),
      *COMMON_TEXT_RUNTIME_PARAMS,
    ],
  )

  def get_model_class(self) -> Type:
    logger.debug("Providing OpenRouterModel class for OpenRouter architecture")
    return OpenRouterModel
