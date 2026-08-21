"""
Anthropic architecture plugin.

Provides Anthropic Claude API-based models.
"""

import logging
from typing import Type

from .base import BaseArchitecture
from ..decorators import architecture
from ..models.api import AnthropicModel
from ..plugins.base import (
  COMMON_TEXT_RUNTIME_PARAMS,
  ParamScope,
  ParamSpec,
  SettingCategory,
)


logger = logging.getLogger(__name__)


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
  category=SettingCategory.API,
  description="Anthropic API Token",
))
@architecture.param(*COMMON_TEXT_RUNTIME_PARAMS)
class AnthropicPlugin(BaseArchitecture):
  """Anthropic architecture plugin providing Claude models via Anthropic API."""

  def get_model_class(self) -> Type:
    logger.debug("Providing AnthropicModel class for Anthropic architecture")
    return AnthropicModel
