"""
Gemma3 specialized transformers architecture plugin.

Provides specialized handling for Gemma3 models that need specific
architecture considerations beyond generic transformers handling.
"""

import logging
import pluggy
from typing import Type

# Internal dependencies
from ..lib.model.transformers import Gemma3Model
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
class TransformersGemma3Plugin:
  """Specialized transformers architecture plugin for Gemma3 models."""

  @hookimpl
  def get_architecture_info(self) -> ArchitectureInfo:
    return ArchitectureInfo(
      name="transformers_gemma3",
      title="Gemma3 Transformers Architecture",
      description="Specialized implementation for Gemma3 transformer models",
      required_args=["huggingface_api_token"]
    )

  @hookimpl
  def get_model_class(self) -> Type:
    logger.debug("Providing Gemma3Model class for transformers_gemma3 architecture")
    return Gemma3Model
