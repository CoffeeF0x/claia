"""
Diffusers architecture plugin.

Provides a generic local implementation for Diffusers-backed image models.
"""

import logging
from typing import Type

from .base import BaseArchitecture
from ..decorators import architecture
from ..plugins.base import ParamScope, ParamSpec, SettingCategory


logger = logging.getLogger(__name__)


@architecture
@architecture.name("diffusers")
@architecture.title("Diffusers Architecture")
@architecture.description("Generic local image generation via Hugging Face Diffusers")
@architecture.param(ParamSpec(
  name="huggingface_api_token",
  type=str,
  scope=ParamScope.INIT,
  secret=True,
  category=SettingCategory.API,
  description="Hugging Face API Token (required for gated image models).",
))
@architecture.param(ParamSpec(
  name="model_path",
  type=str,
  scope=ParamScope.INIT,
  default=None,
  category=SettingCategory.DIRECTORY,
  description="Optional local path for loading a downloaded Diffusers pipeline.",
))
@architecture.param(ParamSpec(
  name="device",
  type=str,
  scope=ParamScope.INIT,
  default="cpu",
  category=SettingCategory.MODEL,
  description="Device used to run the pipeline, such as cpu, cuda, or mps.",
))
@architecture.param(ParamSpec(
  name="defer_loading",
  type=bool,
  scope=ParamScope.INIT,
  default=False,
  category=SettingCategory.MODEL,
  description="Defer pipeline loading until the first generation call.",
))
@architecture.param(ParamSpec(
  name="pipeline_profile",
  type=str,
  scope=ParamScope.INIT,
  default=None,
  category=SettingCategory.MODEL,
  description="Optional pipeline profile for model-family-specific parameter handling.",
))
@architecture.param(ParamSpec(
  name="prompt",
  type=str,
  scope=ParamScope.RUNTIME,
  default=None,
  category=SettingCategory.PROMPT,
  description="Optional prompt override. Defaults to the latest user message.",
))
@architecture.param(ParamSpec(
  name="negative_prompt",
  type=str,
  scope=ParamScope.RUNTIME,
  default=None,
  category=SettingCategory.PROMPT,
  description="Text describing what the image should avoid.",
))
@architecture.param(ParamSpec(
  name="height",
  type=int,
  scope=ParamScope.RUNTIME,
  default=512,
  category=SettingCategory.GENERATION,
  description="Generated image height in pixels.",
))
@architecture.param(ParamSpec(
  name="width",
  type=int,
  scope=ParamScope.RUNTIME,
  default=512,
  category=SettingCategory.GENERATION,
  description="Generated image width in pixels.",
))
@architecture.param(ParamSpec(
  name="num_inference_steps",
  type=int,
  scope=ParamScope.RUNTIME,
  default=30,
  category=SettingCategory.GENERATION,
  description="Number of denoising steps.",
))
@architecture.param(ParamSpec(
  name="guidance_scale",
  type=float,
  scope=ParamScope.RUNTIME,
  default=7.5,
  category=SettingCategory.GENERATION,
  description="Classifier-free guidance scale.",
))
@architecture.param(ParamSpec(
  name="seed",
  type=int,
  scope=ParamScope.RUNTIME,
  default=None,
  category=SettingCategory.GENERATION,
  description="Optional deterministic generation seed.",
))
@architecture.param(ParamSpec(
  name="num_images",
  type=int,
  scope=ParamScope.RUNTIME,
  default=1,
  category=SettingCategory.GENERATION,
  description="Number of images to generate for the prompt.",
))
@architecture.param(ParamSpec(
  name="output_format",
  type=str,
  scope=ParamScope.RUNTIME,
  default="png",
  choices=["png", "jpg", "jpeg", "webp"],
  category=SettingCategory.GENERATION,
  description="Encoded output image format.",
))
class DiffusersPlugin(BaseArchitecture):
  """Generic architecture plugin for local Diffusers image pipelines."""

  def get_model_class(self) -> Type:
    from ..models.transformers.diffusers import DiffusersModel

    logger.debug("Providing DiffusersModel class for diffusers architecture")
    return DiffusersModel
