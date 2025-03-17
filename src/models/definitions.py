# External dependencies
from enum import Enum

# Internal dependencies
from models.api.openai import OpenAITextModel
from models.api.runpod import RunpodTextModel
from models.api.anthropic import AnthropicTextModel
from models.local import MiniCPM3_4B_LocalModel, Qwen2p5_32B_InstructLocalModel
from models.api.openrouter import OpenRouterTextModel
from models.remote.vllm import VLLMTextModel



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
#                         MODEL SOURCE MAPPING                         #
########################################################################
# Maps source identifiers to their implementation classes
sources = {
  "openai": OpenAITextModel,
  "anthropic": AnthropicTextModel,
  "local-minicpm3-4b": MiniCPM3_4B_LocalModel,
  "local-qwen2.5-32b-instruct": Qwen2p5_32B_InstructLocalModel,
  "openrouter": OpenRouterTextModel,
  "vllm": VLLMTextModel
}



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

definitions = {
  # "gpt-3.5-turbo": {
  #   "title": "GPT 3.5 Turbo",
  #   "description": "The latest GPT-3.5 Turbo model with higher accuracy at responding in requested formats and a fix for a bug which caused a text encoding issue for non-English language function calls.",
  #   "capabilities": [ModelCapability.TTT],
  # },
  "gpt-4": {
    "title": "GPT 4",
    "description": "Snapshot of gpt-4 from June 13th 2023 with improved function calling support.",
    "capabilities": [ModelCapability.TTT],
    "sources": {
      "openai": ["gpt-4-0613", "gpt-4"],
      "openrouter": ["openai/gpt-4"]
    }
  },
  # "gpt-4-turbo": {
  #   "title": "GPT 4 Turbo",
  #   "description": "The latest GPT-4 Turbo model with vision capabilities. Vision requests can now use JSON mode and function calling.",
  #   "capabilities": [ModelCapability.TTT],
  # },
  "claude-3-5-sonnet-20240620": {
    "title": "Claude 3.5 Sonnet",
    "description": "Claude 3.5 Sonnet sets new industry benchmarks for graduate-level reasoning (GPQA), undergraduate-level knowledge (MMLU), and coding proficiency (HumanEval). It shows marked improvement in grasping nuance, humor, and complex instructions, and is exceptional at writing high-quality content with a natural, relatable tone.",
    "capabilities": [ModelCapability.TTT],
    "sources": {
      "anthropic": ["claude-3-5-sonnet-20240620"],
      "openrouter": ["anthropic/claude-3-sonnet-20240620"]
    }
  },
  "minicpm3-4b": {
    "title": "MiniCPM3-4B",
    "description": "MiniCPM3-4B is the 3rd generation of MiniCPM series with a 32k context window.",
    "capabilities": [ModelCapability.TTT],
    "sources": {
      "local-minicpm3-4b": ["minicpm3-4b"],
      "vllm": ["openbmb/MiniCPM3-4B"]
    }
  },
  # "qwen2.5-32b-instruct": {
  #   "title": "Qwen2.5-32B-Instruct",
  #   "description": "Qwen2.5 is the latest series of Qwen large language models. For Qwen2.5, we release a number of base language models and instruction-tuned language models ranging from 0.5 to 72 billion parameters.",
  #   "capabilities": [ModelCapability.TTT],
  #   "training_data": "Not specified",
  # },
  # "qwen2.5-72b-instruct": {
  #   "title": "Qwen2.5-72B-Instruct",
  #   "description": "Qwen2.5's largest model with 72B parameters. Features improved capabilities in coding, mathematics, instruction following, and multilingual support for over 29 languages. Specialized in generating structured outputs and long-form content.",
  #   "capabilities": [ModelCapability.TTT],
  #   "training_data": "Not specified",
  # },
  # "mistral-7b": {
  #   "title": "Mistral 7B Instruct",
  #   "description": "Mistral 7B is a 7-billion parameter language model demonstrating state-of-the-art performance among models of comparable size.",
  #   "capabilities": [ModelCapability.TTT],
  #   "training_data": "Not specified",
  # },
  # "mixtral-8x7b": {
  #   "title": "Mixtral 8x7B Instruct",
  #   "description": "Mixtral 8x7B is a Mixture of Experts model with 8 experts of 7B parameters each. It outperforms Llama 2 70B on most benchmarks.",
  #   "capabilities": [ModelCapability.TTT],
  #   "training_data": "Not specified",
  # },
  # "llama2-70b": {
  #   "title": "Llama 2 70B Chat",
  #   "description": "Meta's largest Llama 2 model fine-tuned for chat/instruct scenarios.",
  #   "capabilities": [ModelCapability.TTT],
  #   "training_data": "Up to 2023",
  # },
  # "qwq-32b-preview": {
  #   "title": "QwQ-32B Preview",
  #   "description": "An experimental research model by the Qwen Team focused on advancing AI reasoning capabilities. Features enhanced analytical abilities while having specific limitations in language mixing, recursive reasoning, and safety considerations. Built on Qwen2.5-32B-Instruct base.",
  #   "capabilities": [ModelCapability.TTT],
  #   "training_data": "Not specified",
  # },
  "qwq-32b": {
    "title": "QwQ-32B",
    "description": "The official release of QwQ-32B, a reasoning-focused model from the Qwen team. Built on the Qwen2.5-32B-Instruct base, it features improved reasoning capabilities while maintaining strong performance across general tasks.",
    "capabilities": [ModelCapability.TTT],
    "sources": {
      "vllm": ["Qwen/QwQ-32B"]
    }
  },
  "phi-4": {
    "title": "Phi-4",
    "description": "Microsoft's Phi-4 is a state-of-the-art small language model that delivers exceptional performance with high efficiency. It excels at reasoning, coding, and instruction following while maintaining a compact size compared to larger models.",
    "capabilities": [ModelCapability.TTT],
    "sources": {
      "vllm": ["microsoft/Phi-4"]
    }
  },
  "stable-diffusion-v2": {
    "title": "Stable Diffusion v2",
    "description": "The latest version of Stable Diffusion, with improved text-to-image generation capabilities.",
    "capabilities": [ModelCapability.TTI],
    "sources": {}
  }
}
