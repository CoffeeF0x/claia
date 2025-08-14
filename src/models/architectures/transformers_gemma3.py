"""
Gemma3 specialized transformers architecture plugin.

Provides specialized handling for Gemma3 models that need specific
architecture considerations beyond generic transformers handling.
"""

import logging
import pluggy
from typing import Optional, Type

# Internal dependencies
from .lib.transformers import Gemma3Model


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)

# Create hookimpl decorator for this plugin namespace
hookimpl = pluggy.HookimplMarker("claia_architectures")


########################################################################
#                               CLASSES                                #
########################################################################
class TransformersGemma3Plugin:
  """Specialized transformers architecture plugin for Gemma3 models."""

  @hookimpl
  def get_model_class(self, model_name: str) -> Optional[Type]:
    """
    Get the specialized model class for Gemma3 models.

    This plugin provides specialized handling for Gemma3 models that
    need specific architecture considerations.

    Args:
        model_name: Canonical model name

    Returns:
        Gemma3Model class if this plugin should handle the model, None otherwise
    """
    # This plugin only handles models explicitly assigned to it via definitions
    # The definition file will specify architectures=["transformers_gemma3"]
    logger.debug(f"Providing Gemma3Model class for specialized Gemma3 handling of {model_name}")
    return Gemma3Model
