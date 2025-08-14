"""
Generic transformers architecture plugin.

Provides a generic implementation for most transformer models via HuggingFace transformers library.
For models that need specialized handling, use specific architecture plugins.
"""

import logging
import pluggy
from typing import Optional, Type

# Internal dependencies
from .lib.transformers import GenericTransformerModel


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)

# Create hookimpl decorator for this plugin namespace
hookimpl = pluggy.HookimplMarker("claia_architectures")


########################################################################
#                               CLASSES                                #
########################################################################
class TransformersGenericPlugin:
  """Generic transformers architecture plugin for standard transformer models."""

  @hookimpl
  def get_model_class(self, model_name: str) -> Optional[Type]:
    """
    Get the generic model class for transformer models.

    This plugin provides a generic implementation that works for most
    transformer models. Models requiring specialized handling should
    use specific architecture plugins.

    Args:
        model_name: Canonical model name

    Returns:
        GenericTransformerModel class for generic transformer handling
    """
    # This is a generic plugin - it can handle any transformer model
    # that doesn't need specialized architecture handling
    logger.debug(f"Providing GenericTransformerModel class for generic transformer {model_name}")
    return GenericTransformerModel
