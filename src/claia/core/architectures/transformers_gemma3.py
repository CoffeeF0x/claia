"""
Gemma3 specialized transformers architecture plugin.

Provides specialized handling for Gemma3 models that need specific
architecture considerations beyond generic transformers handling.
"""

import logging
from typing import Type

from .base import BaseArchitecture
from ..models.transformers import Gemma3Model
from ..plugins.base import (
  COMMON_TEXT_RUNTIME_PARAMS,
  ArchitectureInfo,
  ParamScope,
  ParamSpec,
  SettingCategory,
)


logger = logging.getLogger(__name__)


# Gemma3 tunes a handful of generation defaults up from the common baseline;
# the remaining RUNTIME specs are inherited unchanged via the spread below.
_GEMMA3_OVERRIDDEN = {"max_tokens", "temperature", "top_p", "top_k"}


class TransformersGemma3Plugin(BaseArchitecture):
  """Specialized transformers architecture plugin for Gemma3 models."""

  info = ArchitectureInfo(
    name="transformers_gemma3",
    title="Gemma3 Transformers Architecture",
    description="Specialized implementation for Gemma3 transformer models",
    params=[
      ParamSpec(
        name="huggingface_api_token",
        type=str,
        scope=ParamScope.INIT,
        secret=True,
        category=SettingCategory.API,
        description="Hugging Face API Token (required for gated Gemma3 checkpoints)",
      ),
      ParamSpec(name="max_tokens", type=int, scope=ParamScope.RUNTIME, default=2048,
                category=SettingCategory.GENERATION,
                description="Maximum number of tokens to generate."),
      ParamSpec(name="temperature", type=float, scope=ParamScope.RUNTIME, default=0.8,
                category=SettingCategory.GENERATION,
                description="Sampling temperature."),
      ParamSpec(name="top_p", type=float, scope=ParamScope.RUNTIME, default=0.95,
                category=SettingCategory.GENERATION,
                description="Nucleus sampling probability mass."),
      ParamSpec(name="top_k", type=int, scope=ParamScope.RUNTIME, default=40,
                category=SettingCategory.GENERATION,
                description="Restrict sampling to the top-k tokens."),
      *[p for p in COMMON_TEXT_RUNTIME_PARAMS if p.name not in _GEMMA3_OVERRIDDEN],
    ],
  )

  def get_model_class(self) -> Type:
    logger.debug("Providing Gemma3Model class for transformers_gemma3 architecture")
    return Gemma3Model
