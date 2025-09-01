"""
Generic transformers architecture plugin.

Provides a generic implementation for most transformer models via HuggingFace transformers library.
For models that need specialized handling, use specific architecture plugins.
"""

import logging
import pluggy
from typing import Type

# Internal dependencies
from ..lib.model.transformers import GenericTransformerModel
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
class TransformersGenericPlugin:
  """Generic transformers architecture plugin for standard transformer models."""

  @hookimpl
  def get_architecture_info(self) -> ArchitectureInfo:
    return ArchitectureInfo(
      name="transformers_generic",
      title="Generic Transformers Architecture",
      description="Generic HF Transformers implementation",
      required_args=["huggingface_api_token"]
    )

  @hookimpl
  def get_model_class(self) -> Type:
    # Generic plugin that can handle a wide variety of transformer models
    logger.debug("Providing GenericTransformerModel class for transformers_generic architecture")
    return GenericTransformerModel
