"""
Anthropic architecture plugin.

Provides Anthropic Claude API-based models.
"""

import logging
import pluggy
from typing import Type

# Internal dependencies
from ..models.api import AnthropicModel
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
class AnthropicPlugin:
  """Anthropic architecture plugin providing Claude models via Anthropic API."""

  @hookimpl
  def get_architecture_info(self) -> ArchitectureInfo:
    return ArchitectureInfo(
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

  @hookimpl
  def get_model_class(self) -> Type:
    logger.debug("Providing AnthropicModel class for Anthropic architecture")
    return AnthropicModel
