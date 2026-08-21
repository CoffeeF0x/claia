"""
Text-to-speech architecture plugin.

Provides a capability-oriented local TTS architecture. Model-specific
runtimes such as Qwen3-TTS live behind backend adapters.
"""

import logging
from typing import Type

from .base import BaseArchitecture
from ..decorators import architecture
from ..plugins.base import ParamScope, ParamSpec, SettingCategory


logger = logging.getLogger(__name__)


@architecture
@architecture.name("tts")
@architecture.title("Text-to-Speech Architecture")
@architecture.description("Generic local text-to-speech generation")
@architecture.param(ParamSpec(
  name="huggingface_api_token",
  type=str,
  scope=ParamScope.INIT,
  secret=True,
  category=SettingCategory.API,
  description="Hugging Face API Token (required for gated audio models).",
))
@architecture.param(ParamSpec(
  name="model_path",
  type=str,
  scope=ParamScope.INIT,
  default=None,
  category=SettingCategory.DIRECTORY,
  description="Optional local path for loading a downloaded TTS model.",
))
@architecture.param(ParamSpec(
  name="device",
  type=str,
  scope=ParamScope.INIT,
  default="cpu",
  category=SettingCategory.MODEL,
  description="Device used to run the model, such as cpu, cuda, or cuda:0.",
))
@architecture.param(ParamSpec(
  name="defer_loading",
  type=bool,
  scope=ParamScope.INIT,
  default=False,
  category=SettingCategory.MODEL,
  description="Defer model loading until the first generation call.",
))
@architecture.param(ParamSpec(
  name="dtype",
  type=str,
  scope=ParamScope.INIT,
  default="auto",
  choices=["auto", "float32", "float16", "bfloat16"],
  category=SettingCategory.MODEL,
  description="Model dtype for local inference.",
))
@architecture.param(ParamSpec(
  name="tts_backend",
  type=str,
  scope=ParamScope.INIT,
  default="qwen3_tts",
  choices=["qwen3_tts"],
  category=SettingCategory.MODEL,
  description="Local TTS backend adapter.",
))
@architecture.param(ParamSpec(
  name="prompt",
  type=str,
  scope=ParamScope.RUNTIME,
  default=None,
  category=SettingCategory.PROMPT,
  description="Optional text override. Defaults to the latest user message.",
))
@architecture.param(ParamSpec(
  name="language",
  type=str,
  scope=ParamScope.RUNTIME,
  default="English",
  category=SettingCategory.GENERATION,
  description="Language label passed to the TTS backend.",
))
@architecture.param(ParamSpec(
  name="voice",
  type=str,
  scope=ParamScope.RUNTIME,
  default=None,
  category=SettingCategory.GENERATION,
  description="Optional voice or voice preset when supported by a backend.",
))
@architecture.param(ParamSpec(
  name="reference_audio_path",
  type=str,
  scope=ParamScope.RUNTIME,
  default=None,
  category=SettingCategory.GENERATION,
  description="Reference audio path for voice cloning. Required by Qwen3-TTS Base.",
))
@architecture.param(ParamSpec(
  name="response_format",
  type=str,
  scope=ParamScope.RUNTIME,
  default="wav",
  choices=["wav"],
  category=SettingCategory.GENERATION,
  description="Encoded audio output format.",
))
@architecture.param(ParamSpec(
  name="sample_rate",
  type=int,
  scope=ParamScope.RUNTIME,
  default=None,
  category=SettingCategory.GENERATION,
  description="Optional requested output sample rate.",
))
class TTSPlugin(BaseArchitecture):
  """Generic architecture plugin for local text-to-speech models."""

  def get_model_class(self) -> Type:
    from ..models.transformers.tts import LocalTTSModel

    logger.debug("Providing LocalTTSModel class for tts architecture")
    return LocalTTSModel
