"""
Anthropic architecture plugin.

Provides Anthropic Claude API-based models.
"""

import logging
from typing import Type

from .base import BaseArchitecture
from ..models.api import AnthropicModel
from ..plugins.base import ArchitectureInfo, ParamScope, ParamSpec, SettingCategory


logger = logging.getLogger(__name__)


class AnthropicPlugin(BaseArchitecture):
  """Anthropic architecture plugin providing Claude models via Anthropic API."""

  info = ArchitectureInfo(
    name="anthropic",
    title="Anthropic API Architecture",
    description="Implements Anthropic Claude API-backed models",
    params=[
      ParamSpec(
        name="anthropic_api_token",
        type=str,
        scope=ParamScope.INIT,
        required=True,
        secret=True,
        category=SettingCategory.API,
        description="Anthropic API Token",
      ),
    ],
  )

  def get_model_class(self) -> Type:
    logger.debug("Providing AnthropicModel class for Anthropic architecture")
    return AnthropicModel
