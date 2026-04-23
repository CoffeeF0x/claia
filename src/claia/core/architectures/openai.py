"""
OpenAI architecture plugin.

Provides OpenAI API-based models like GPT-4, GPT-3.5-turbo, etc.
"""

import logging
from typing import Type

from .base import BaseArchitecture
from ..models.api import OpenAIModel
from ..plugins.base import ArchitectureInfo, ParamScope, ParamSpec, SettingCategory


logger = logging.getLogger(__name__)


class OpenAIPlugin(BaseArchitecture):
  """OpenAI architecture plugin providing GPT models via OpenAI API."""

  info = ArchitectureInfo(
    name="openai",
    title="OpenAI API Architecture",
    description="Implements OpenAI chat/completions API-backed models",
    params=[
      ParamSpec(
        name="openai_api_token",
        type=str,
        scope=ParamScope.INIT,
        required=True,
        secret=True,
        category=SettingCategory.API,
        description="OpenAI API Token",
      ),
    ],
  )

  def get_model_class(self) -> Type:
    logger.debug("Providing OpenAIModel class for OpenAI architecture")
    return OpenAIModel
