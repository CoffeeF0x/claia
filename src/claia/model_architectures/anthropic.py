"""
Anthropic architecture plugin.

Provides Anthropic Claude API-based models.
"""

import logging
import pluggy
from typing import Type

# Internal dependencies
from ..lib.model.api import AnthropicModel
from ..hooks.architecture import ArchitectureInfo


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
      required_args=["anthropic_api_token"]
    )

  @hookimpl
  def get_model_class(self) -> Type:
    logger.debug("Providing AnthropicModel class for Anthropic architecture")
    return AnthropicModel
