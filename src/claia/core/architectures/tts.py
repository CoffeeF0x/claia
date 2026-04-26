"""
Text-to-speech architecture plugin.

Provides a capability-oriented local TTS architecture. Model-specific
runtimes such as Qwen3-TTS live behind backend adapters.
"""

import logging
from typing import Type

from .base import BaseArchitecture
from ..plugins.base import ArchitectureInfo, ParamScope, ParamSpec, SettingCategory


logger = logging.getLogger(__name__)


class TTSPlugin(BaseArchitecture):
  """Generic architecture plugin for local text-to-speech models."""

  info = ArchitectureInfo(
    name="tts",
    title="Text-to-Speech Architecture",
    description="Generic local text-to-speech generation",
    params=[
      ParamSpec(
        name="huggingface_api_token",
        type=str,
        scope=ParamScope.INIT,
        secret=True,
        category=SettingCategory.API,
        description="Hugging Face API Token (required for gated audio models).",
      ),
      ParamSpec(
        name="model_path",
        type=str,
        scope=ParamScope.INIT,
        default=None,
        category=SettingCategory.DIRECTORY,
        description="Optional local path for loading a downloaded TTS model.",
      ),
      ParamSpec(
        name="device",
        type=str,
        scope=ParamScope.INIT,
        default="cpu",
        category=SettingCategory.MODEL,
        description="Device used to run the model, such as cpu, cuda, or cuda:0.",
      ),
      ParamSpec(
        name="defer_loading",
        type=bool,
        scope=ParamScope.INIT,
        default=False,
        category=SettingCategory.MODEL,
        description="Defer model loading until the first generation call.",
      ),
      ParamSpec(
        name="dtype",
        type=str,
        scope=ParamScope.INIT,
        default="auto",
        choices=["auto", "float32", "float16", "bfloat16"],
        category=SettingCategory.MODEL,
        description="Model dtype for local inference.",
      ),
      ParamSpec(
        name="tts_backend",
        type=str,
        scope=ParamScope.INIT,
        default="qwen3_tts",
        choices=["qwen3_tts"],
        category=SettingCategory.MODEL,
        description="Local TTS backend adapter.",
      ),
      ParamSpec(
        name="prompt",
        type=str,
        scope=ParamScope.RUNTIME,
        default=None,
        category=SettingCategory.PROMPT,
        description="Optional text override. Defaults to the latest user message.",
      ),
      ParamSpec(
        name="language",
        type=str,
        scope=ParamScope.RUNTIME,
        default="English",
        category=SettingCategory.GENERATION,
        description="Language label passed to the TTS backend.",
      ),
      ParamSpec(
        name="voice",
        type=str,
        scope=ParamScope.RUNTIME,
        default=None,
        category=SettingCategory.GENERATION,
        description="Optional voice or voice preset when supported by a backend.",
      ),
      ParamSpec(
        name="reference_audio_path",
        type=str,
        scope=ParamScope.RUNTIME,
        default=None,
        category=SettingCategory.GENERATION,
        description="Optional reference audio path for voice cloning.",
      ),
      ParamSpec(
        name="reference_text",
        type=str,
        scope=ParamScope.RUNTIME,
        default=None,
        category=SettingCategory.GENERATION,
        description="Transcript for the reference audio.",
      ),
      ParamSpec(
        name="response_format",
        type=str,
        scope=ParamScope.RUNTIME,
        default="wav",
        choices=["wav"],
        category=SettingCategory.GENERATION,
        description="Encoded audio output format.",
      ),
      ParamSpec(
        name="sample_rate",
        type=int,
        scope=ParamScope.RUNTIME,
        default=None,
        category=SettingCategory.GENERATION,
        description="Optional requested output sample rate.",
      ),
    ],
  )

  def get_model_class(self) -> Type:
    from ..models.transformers.tts import LocalTTSModel

    logger.debug("Providing LocalTTSModel class for tts architecture")
    return LocalTTSModel
