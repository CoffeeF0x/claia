"""
OpenAI architecture plugin.

Provides OpenAI API-based models like GPT-4, GPT-3.5-turbo, etc.
"""

import logging
import pluggy
from typing import Optional, Type

# Internal dependencies
from .lib.api import OpenAIModel


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
  def get_model_class(self, model_name: str) -> Optional[Type]:
    """
    Get the model class for OpenAI models.

    Args:
        model_name: Canonical model name

    Returns:
        OpenAIModel class if this is an OpenAI model, None otherwise
    """
    # This plugin only handles models explicitly assigned to it via definitions
    # The definition file will specify architectures=["openai"]
    logger.debug(f"Providing OpenAIModel class for {model_name}")
    return OpenAIModel
