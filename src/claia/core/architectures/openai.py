"""
OpenAI architecture plugin.

Provides OpenAI API-based models like GPT-4, GPT-3.5-turbo, etc.
"""

import logging
import pluggy
from typing import Type

# Internal dependencies
from ..models.api import OpenAIModel
from ..plugins.base import ArchitectureInfo, ParamScope, ParamSpec, SettingCategory


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)

# Create hookimpl decorator for this plugin namespace
hookimpl = pluggy.HookimplMarker("claia_architectures")


########################################################################
#                               CLASSES                                #
########################################################################
class OpenAIPlugin:
  """OpenAI architecture plugin providing GPT models via OpenAI API."""

  @hookimpl
  def get_architecture_info(self) -> ArchitectureInfo:
    return ArchitectureInfo(
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

  @hookimpl
  def get_model_class(self) -> Type:
    logger.debug("Providing OpenAIModel class for OpenAI architecture")
    return OpenAIModel
