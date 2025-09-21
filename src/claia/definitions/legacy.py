"""
Legacy model definitions plugin.

Provides comprehensive model definitions for legacy models including GPT, Claude, and various open-source models.
"""

import logging
import pluggy
from typing import Dict, List, Optional
from dataclasses import dataclass

# Internal dependencies
from ..hooks.definition import ModelDefinition
from claia.lib.enums.model import ModelCapability, IOType


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)
hookimpl = pluggy.HookimplMarker("claia_definitions")


########################################################################
#                          DEFAULT SETTINGS                            #
########################################################################
# Default generation settings for models
# Individual models can override specific settings as needed
DEFAULT_SETTINGS = {
  "max_new_tokens": 8192,
  "top_p": 0.7,
  "temperature": 0.7
}


########################################################################
#                          MODEL DEFINITIONS                           #
########################################################################
class LegacyDefinitionsPlugin:
  """Legacy model definitions plugin containing comprehensive model metadata."""

  @hookimpl
  def get_definitions(self) -> Dict[str, ModelDefinition]:
    """Get legacy model definitions."""
    definitions = {
      "gemma-3-1b": ModelDefinition(
        title="Gemma 3 1B",
        description="Gemma 3 1B is Google's smallest text-only model in the Gemma 3 family. It features a 32K context window and supports English language only.",
        capabilities=["chat", "text-generation"],
        deployments=["local"],
        architectures=["transformers_gemma3"],
        aliases=["gemma3-1b", "gemma-1b", "gemma3-small"],
        identifiers={
          "transformers_gemma3": "google/gemma-3-1b-it"
        }
      ),
      "gemma-3-4b": ModelDefinition(
        title="Gemma 3 4B",
        description="Gemma 3 4B is a multimodal model from Google's Gemma 3 family. It supports text and image inputs, has a 128K context window, and works with 140+ languages.",
        capabilities=["chat", "text-generation", "image-understanding", "multimodal"],
        deployments=["local"],
        architectures=["transformers_gemma3"],
        aliases=["gemma3-4b", "gemma-4b", "gemma3-medium"],
        identifiers={
          "transformers_gemma3": "google/gemma-3-4b"
        }
      ),
      "gemma-3-12b": ModelDefinition(
        title="Gemma 3 12B",
        description="Gemma 3 12B is a multimodal model from Google's Gemma 3 family. It supports text and image inputs, has a 128K context window, and works with 140+ languages.",
        capabilities=["chat", "text-generation", "image-understanding", "multimodal"],
        deployments=["local"],
        architectures=["transformers_gemma3"],
        aliases=["gemma3-12b", "gemma-12b", "gemma3-large"],
        identifiers={
          "transformers_gemma3": "google/gemma-3-12b"
        }
      ),
      "gemma-3-27b": ModelDefinition(
        title="Gemma 3 27B",
        description="Gemma 3 27B is Google's largest multimodal model in the Gemma 3 family. It supports text and image inputs, has a 128K context window, and works with 140+ languages. It offers performance comparable to much larger models.",
        capabilities=["chat", "text-generation", "image-understanding", "multimodal"],
        deployments=["local"],
        architectures=["transformers_gemma3"],
        aliases=["gemma3-27b", "gemma-27b", "gemma3-xl", "gemma3-xlarge"],
        identifiers={
          "transformers_gemma3": "google/gemma-3-27b"
        }
      ),
      "minicpm3-4b": ModelDefinition(
        title="MiniCPM3-4B",
        description="MiniCPM3-4B is the 3rd generation of MiniCPM series with a 32k context window.",
        capabilities=["chat", "text-generation"],
        deployments=["local"],
        architectures=["transformers_generic"],
        aliases=["minicpm", "minicpm3"],
        identifiers={
          "transformers_generic": "openbmb/MiniCPM3-4B"
        }
      ),
      "qwen2.5-32b-instruct": ModelDefinition(
        title="Qwen 2.5 32B Instruct",
        description="Qwen 2.5 32B Instruct is a member of the Qwen2 series, a second-generation foundation model developed by Qwen team at Alibaba Cloud.",
        capabilities=["chat", "instruction-following", "reasoning"],
        deployments=["local"],
        architectures=["transformers_generic"],
        aliases=["qwen2.5", "qwen-32b", "qwen"],
        identifiers={
          "transformers_generic": "qwen/qwen2.5-32b-instruct"
        }
      ),
      "qwq-32b": ModelDefinition(
        title="QwQ-32B",
        description="The official release of QwQ-32B, a reasoning-focused model from the Qwen team. Built on the Qwen2.5-32B-Instruct base, it features improved reasoning capabilities while maintaining strong performance across general tasks.",
        capabilities=["chat", "reasoning", "mathematical-reasoning"],
        deployments=["local"],
        architectures=["transformers_generic"],
        aliases=["qwq", "qwq32b"],
        identifiers={
          "transformers_generic": "qwen/qwq-32b"
        }
      ),
      "phi-4": ModelDefinition(
        title="Phi-4",
        description="Microsoft's Phi-4 is a state-of-the-art small language model that delivers exceptional performance with high efficiency. It excels at reasoning, coding, and instruction following while maintaining a compact size compared to larger models.",
        capabilities=["chat", "reasoning", "coding", "instruction-following"],
        deployments=["local"],
        architectures=["transformers_generic"],
        aliases=["phi4", "phi"],
        identifiers={
          "transformers_generic": "microsoft/phi-4"
        }
      ),
      "stable-diffusion-v2": ModelDefinition(
        title="Stable Diffusion v2",
        description="The latest version of Stable Diffusion, with improved text-to-image generation capabilities.",
        capabilities=["text-to-image", "image-generation"],
        deployments=["local"],
        architectures=[],
        aliases=["sd-v2", "sd2", "stable-diffusion-2"]
      ),
      "stable-diffusion-v1-5": ModelDefinition(
        title="Stable Diffusion v1.5",
        description="A smaller version of Stable Diffusion that requires less VRAM, good for testing or on systems with limited resources.",
        capabilities=["text-to-image", "image-generation"],
        deployments=["local"],
        architectures=[],
        aliases=["sd-v1.5", "sd1.5", "stable-diffusion-1.5"]
      ),
      "llama-3.2-1b": ModelDefinition(
        title="Llama 3.2 1B",
        description="Meta's Llama 3.2 1B is a compact text generation model that delivers efficient performance for chat and text generation tasks while maintaining a small footprint.",
        capabilities=["chat", "text-generation"],
        deployments=["local"],
        architectures=["transformers_generic"],
        aliases=["llama3.2-1b", "llama-1b", "llama3-1b"],
        identifiers={
          "transformers_generic": "meta-llama/Llama-3.2-1B"
        }
      ),
      "dummy-model": ModelDefinition(
        title="Dummy Model",
        description="A dummy model that returns a predefined story. Used for testing streaming capabilities.",
        capabilities=["text-generation", "chat"],
        deployments=["dummy"],
        architectures=["dummy"],
        aliases=["dummy"]
      )
    }

    return definitions
