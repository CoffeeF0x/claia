"""
OpenAI architecture plugin.

Provides OpenAI API-based models like GPT-4, GPT-3.5-turbo, etc.
"""

import logging
import pluggy
from typing import Type

# Internal dependencies
from ..lib.model.api import OpenAIModel
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
class OpenAIPlugin:
  """OpenAI architecture plugin providing GPT models via OpenAI API."""

  @hookimpl
  def get_architecture_info(self) -> ArchitectureInfo:
    return ArchitectureInfo(
      name="openai",
      title="OpenAI API Architecture",
      description="Implements OpenAI chat/completions API-backed models",
      required_args=["openai_api_token"]
    )

  @hookimpl
  def get_model_class(self) -> Type:
    logger.debug("Providing OpenAIModel class for OpenAI architecture")
    return OpenAIModel
