"""
Generic transformers architecture plugin.

Provides a generic implementation for most transformer models via HuggingFace transformers library.
For models that need specialized handling, use specific architecture plugins.
"""

import logging
from typing import Type

from .base import BaseArchitecture
from ..models.transformers import GenericTransformerModel
from ..plugins.base import (
  COMMON_TEXT_RUNTIME_PARAMS,
  ArchitectureInfo,
  ParamScope,
  ParamSpec,
  SettingCategory,
)


logger = logging.getLogger(__name__)


class TransformersGenericPlugin(BaseArchitecture):
  """Generic transformers architecture plugin for standard transformer models."""

  info = ArchitectureInfo(
    name="transformers_generic",
    title="Generic Transformers Architecture",
    description="Generic HF Transformers implementation",
    params=[
      ParamSpec(
        name="huggingface_api_token",
        type=str,
        scope=ParamScope.INIT,
        secret=True,
        category=SettingCategory.API,
        description="Hugging Face API Token (required for gated models)",
      ),
      *COMMON_TEXT_RUNTIME_PARAMS,
    ],
  )

  def get_model_class(self) -> Type:
    logger.debug("Providing GenericTransformerModel class for transformers_generic architecture")
    return GenericTransformerModel
