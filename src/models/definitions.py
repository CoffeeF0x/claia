# External dependencies
from enum import Enum



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
#                                ENUMS                                 #
########################################################################
class ModelCapability(Enum):
  """Capabilities of a model."""
  TTT = "text-to-text"
  TTI = "text-to-image"
  ITT = "image-to-text"
  TTS = "text-to-speech"
  STT = "speech-to-text"
  TTA = "text-to-audio"
  TAA = "text-and-audio"
  TAI = "text-and-image"
  # LLM = "large-language-model"
  # SLM = "small-language-model"

class IOType(Enum):
  """Input/output types of a model."""
  TEXT  = ["txt"]
  IMAGE = ["png", "jpg"]
  AUDIO = ["mp3", "wav"]



########################################################################
#                          MODEL DEFINITIONS                           #
########################################################################
# General model information and metadata
# Source-specific details are in the sources mapping
# Each model entry contains:
#   - title: Display name
#   - description: Detailed description of the model
#   - variants: List of model versions/variants
#   - sources: Available providers/platforms
#   - capabilities: List of supported operations
#   - inputs/outputs: Supported formats
#   - attributes: Technical specifications
#   - settings: Model-specific settings for generation (overrides defaults)

definitions = {
  "gpt-4": {
    "title": "GPT 4",
    "description": "Snapshot of gpt-4 from June 13th 2023 with improved function calling support.",
    "capabilities": [ModelCapability.TTT],
    "sources": {
      "openai": ["gpt-4-0613", "gpt-4"],
      "openrouter": ["openai/gpt-4"]
    },
  },
  "claude-3-5-sonnet": {
    "title": "Claude 3.5 Sonnet",
    "description": "Claude 3.5 Sonnet sets new industry benchmarks for graduate-level reasoning (GPQA), undergraduate-level knowledge (MMLU), and coding proficiency (HumanEval). It shows marked improvement in grasping nuance, humor, and complex instructions, and is exceptional at writing high-quality content with a natural, relatable tone.",
    "capabilities": [ModelCapability.TTT],
    "sources": {
      "anthropic": ["claude-3-5-sonnet-20240620"],
      "openrouter": ["anthropic/claude-3-sonnet-20240620"]
    },
  },
  "minicpm3-4b": {
    "title": "MiniCPM3-4B",
    "description": "MiniCPM3-4B is the 3rd generation of MiniCPM series with a 32k context window.",
    "capabilities": [ModelCapability.TTT],
    "sources": {
      "transformers": ["openbmb/MiniCPM3-4B"],
      "vllm": ["openbmb/MiniCPM3-4B"]
    },
    "settings": {
      "max_new_tokens": 4096,
      "temperature": 0.8
    }
  },
  "qwen2.5-32b-instruct": {
    "title": "Qwen 2.5 32B Instruct",
    "description": "Qwen 2.5 32B Instruct is a member of the Qwen2 series, a second-generation foundation model developed by Qwen team at Alibaba Cloud.",
    "capabilities": [ModelCapability.TTT],
    "sources": {
      "transformers": ["Qwen/Qwen2.5-32B-Instruct"],
      "vllm": ["Qwen/Qwen2.5-32B-Instruct"]
    }
  },
  "qwq-32b": {
    "title": "QwQ-32B",
    "description": "The official release of QwQ-32B, a reasoning-focused model from the Qwen team. Built on the Qwen2.5-32B-Instruct base, it features improved reasoning capabilities while maintaining strong performance across general tasks.",
    "capabilities": [ModelCapability.TTT],
    "sources": {
      "transformers": ["Qwen/QwQ-32B"],
      "vllm": ["Qwen/QwQ-32B"]
    }
  },
  "phi-4": {
    "title": "Phi-4",
    "description": "Microsoft's Phi-4 is a state-of-the-art small language model that delivers exceptional performance with high efficiency. It excels at reasoning, coding, and instruction following while maintaining a compact size compared to larger models.",
    "capabilities": [ModelCapability.TTT],
    "sources": {
      "transformers": ["microsoft/Phi-4"],
      "vllm": ["microsoft/Phi-4"]
    },
  },
  "stable-diffusion-v2": {
    "title": "Stable Diffusion v2",
    "description": "The latest version of Stable Diffusion, with improved text-to-image generation capabilities.",
    "capabilities": [ModelCapability.TTI],
    "sources": {}
  }
}