"""
Anthropic architecture plugin.

Provides Anthropic Claude API-based models.
"""

import logging
import pluggy
from typing import Optional, Type

# Internal dependencies
from .lib.api import AnthropicModel


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
  def get_model_class(self, model_name: str) -> Optional[Type]:
    """
    Get the model class for Anthropic models.

    Args:
        model_name: Canonical model name

    Returns:
        AnthropicModel class if this is an Anthropic model, None otherwise
    """
    # This plugin only handles models explicitly assigned to it via definitions
    # The definition file will specify architectures=["anthropic"]
    logger.debug(f"Providing AnthropicModel class for {model_name}")
    return AnthropicModel
