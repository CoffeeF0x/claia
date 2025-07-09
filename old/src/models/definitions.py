# Internal dependencies
from enums import ModelCapability, IOType



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
#   - aliases: Alternative names that can be used to reference this model

model_definitions = {
  "gpt-4": {
    "title": "GPT 4",
    "description": "Snapshot of gpt-4 from June 13th 2023 with improved function calling support.",
    "capabilities": [ModelCapability.TTT],
    "sources": {
      "openai": ["gpt-4-0613", "gpt-4"],
      "openrouter": ["openai/gpt-4"]
    },
    "aliases": ["gpt4", "gpt-4-0613"]
  },
  "claude-3-5-sonnet": {
    "title": "Claude 3.5 Sonnet",
    "description": "Claude 3.5 Sonnet sets new industry benchmarks for graduate-level reasoning (GPQA), undergraduate-level knowledge (MMLU), and coding proficiency (HumanEval). It shows marked improvement in grasping nuance, humor, and complex instructions, and is exceptional at writing high-quality content with a natural, relatable tone.",
    "capabilities": [ModelCapability.TTT],
    "sources": {
      "anthropic": ["claude-3-5-sonnet-20240620"],
      "openrouter": ["anthropic/claude-3-sonnet-20240620"]
    },
    "aliases": ["claude3.5", "claude-3.5", "claude-3-5"]
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
    },
    "aliases": ["minicpm", "minicpm3"]
  },
  "qwen2.5-32b-instruct": {
    "title": "Qwen 2.5 32B Instruct",
    "description": "Qwen 2.5 32B Instruct is a member of the Qwen2 series, a second-generation foundation model developed by Qwen team at Alibaba Cloud.",
    "capabilities": [ModelCapability.TTT],
    "sources": {
      "transformers": ["Qwen/Qwen2.5-32B-Instruct"],
      "vllm": ["Qwen/Qwen2.5-32B-Instruct"]
    },
    "aliases": ["qwen2.5", "qwen-32b", "qwen"]
  },
  "qwq-32b": {
    "title": "QwQ-32B",
    "description": "The official release of QwQ-32B, a reasoning-focused model from the Qwen team. Built on the Qwen2.5-32B-Instruct base, it features improved reasoning capabilities while maintaining strong performance across general tasks.",
    "capabilities": [ModelCapability.TTT],
    "sources": {
      "transformers": ["Qwen/QwQ-32B"],
      "vllm": ["Qwen/QwQ-32B"]
    },
    "aliases": ["qwq", "qwq32b"]
  },
  "phi-4": {
    "title": "Phi-4",
    "description": "Microsoft's Phi-4 is a state-of-the-art small language model that delivers exceptional performance with high efficiency. It excels at reasoning, coding, and instruction following while maintaining a compact size compared to larger models.",
    "capabilities": [ModelCapability.TTT],
    "sources": {
      "transformers": ["microsoft/Phi-4"],
      "vllm": ["microsoft/Phi-4"]
    },
    "aliases": ["phi4", "phi"]
  },
  "gemma-3-1b": {
    "title": "Gemma 3 1B",
    "description": "Gemma 3 1B is Google's smallest text-only model in the Gemma 3 family. It features a 32K context window and supports English language only.",
    "capabilities": [ModelCapability.TTT],
    "sources": {
      "transformers": ["google/gemma-3-1b-it", "google/gemma-3-1b-pt"]
    },
    "settings": {
      "max_new_tokens": 4096,
      "temperature": 0.7
    },
    "class_overrides": {
      "transformers": {
        ModelCapability.DEFAULT: "gemma-3",
        ModelCapability.TTT: "gemma-3"
      }
    },
    "aliases": ["gemma3-1b", "gemma-1b", "gemma3-small"]
  },
  "gemma-3-4b": {
    "title": "Gemma 3 4B",
    "description": "Gemma 3 4B is a multimodal model from Google's Gemma 3 family. It supports text and image inputs, has a 128K context window, and works with 140+ languages.",
    "capabilities": [ModelCapability.TTT, ModelCapability.ITT, ModelCapability.TAI],
    "sources": {
      "transformers": ["google/gemma-3-4b-it", "google/gemma-3-4b-pt"]
    },
    "settings": {
      "max_new_tokens": 4096,
      "temperature": 0.7
    },
    "class_overrides": {
      "transformers": {
        ModelCapability.DEFAULT: "gemma-3",
        ModelCapability.TAI: "gemma-3"
      }
    },
    "aliases": ["gemma3-4b", "gemma-4b", "gemma3-medium"]
  },
  "gemma-3-12b": {
    "title": "Gemma 3 12B",
    "description": "Gemma 3 12B is a multimodal model from Google's Gemma 3 family. It supports text and image inputs, has a 128K context window, and works with 140+ languages.",
    "capabilities": [ModelCapability.TTT, ModelCapability.ITT, ModelCapability.TAI],
    "sources": {
      "transformers": ["google/gemma-3-12b-it", "google/gemma-3-12b-pt"]
    },
    "settings": {
      "max_new_tokens": 4096,
      "temperature": 0.7
    },
    "class_overrides": {
      "transformers": {
        ModelCapability.DEFAULT: "gemma-3",
        ModelCapability.TAI: "gemma-3"
      }
    },
    "aliases": ["gemma3-12b", "gemma-12b", "gemma3-large"]
  },
  "gemma-3-27b": {
    "title": "Gemma 3 27B",
    "description": "Gemma 3 27B is Google's largest multimodal model in the Gemma 3 family. It supports text and image inputs, has a 128K context window, and works with 140+ languages. It offers performance comparable to much larger models.",
    "capabilities": [ModelCapability.TTT, ModelCapability.ITT, ModelCapability.TAI],
    "sources": {
      "transformers": ["google/gemma-3-27b-it", "google/gemma-3-27b-pt"]
    },
    "settings": {
      "max_new_tokens": 4096,
      "temperature": 0.7
    },
    "class_overrides": {
      "transformers": {
        ModelCapability.DEFAULT: "gemma-3",
        ModelCapability.TAI: "gemma-3"
      }
    },
    "aliases": ["gemma3-27b", "gemma-27b", "gemma3-xl", "gemma3-xlarge"]
  },
  "stable-diffusion-v2": {
    "title": "Stable Diffusion v2",
    "description": "The latest version of Stable Diffusion, with improved text-to-image generation capabilities.",
    "capabilities": [ModelCapability.TTI],
    "sources": {
      "transformers": ["stabilityai/stable-diffusion-2"]
    },
    "settings": {
      "height": 768,
      "width": 768,
      "num_inference_steps": 30,
      "guidance_scale": 7.5
    },
    "class_overrides": {
      "transformers": {
        ModelCapability.DEFAULT: "stable-diffusion",
        ModelCapability.TTI: "stable-diffusion"
      }
    },
    "aliases": ["sd-v2", "sd2", "stable-diffusion-2"]
  },
  "stable-diffusion-v1-5": {
    "title": "Stable Diffusion v1.5",
    "description": "A smaller version of Stable Diffusion that requires less VRAM, good for testing or on systems with limited resources.",
    "capabilities": [ModelCapability.TTI],
    "sources": {
      "transformers": ["runwayml/stable-diffusion-v1-5"]
    },
    "settings": {
      "height": 512,
      "width": 512,
      "num_inference_steps": 30,
      "guidance_scale": 7.5
    },
    "class_overrides": {
      "transformers": {
        ModelCapability.DEFAULT: "stable-diffusion",
        ModelCapability.TTI: "stable-diffusion"
      }
    },
    "aliases": ["sd-v1.5", "sd1.5", "stable-diffusion-1.5"]
  },
  "dummy-model": {
    "title": "Dummy Model",
    "description": "A dummy model that returns a predefined story. Used for testing streaming capabilities.",
    "capabilities": [ModelCapability.TTT],
    "sources": {
      "dummy": ["dummy-model"]
    },
    "settings": {
      "words_per_second": 20
    },
    "aliases": ["dummy", "dummy-model"]
  }
}