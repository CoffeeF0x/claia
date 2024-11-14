from models.openai import OpenAITextModel
from models.runpod import RunpodTextModel
from models.anthropic import AnthropicTextModel
from models.local import MiniCPM3_4B_LocalModel, Qwen2p5_32B_InstructLocalModel
from models.openrouter import OpenRouterTextModel


##################################################
#              MODEL SOURCE MAPPING              #
##################################################
# Maps source identifiers to their implementation details
# Structure:
#   - class: Implementation class
#   - models: Dictionary of supported models
#     - model_id: Internal model name used by the source
#     - attributes: Source-specific model capabilities
sources = {
  "openai": {
    "class": OpenAITextModel,
    "inputs": ["text"],
    "outputs": ["text"],
    "models": {
      "gpt-3.5-turbo": {
        "model_id": "gpt-3.5-turbo-0125",
        "variants": ["gpt-3.5-turbo-0125", "gpt-3.5-turbo-1106", "gpt-3.5-turbo-instruct"],
        "attributes": {
          "max_output": 4096,
          "context": 16385,
        }
      },
      "gpt-4": {
        "model_id": "gpt-4-0613",
        "variants": ["gpt-4-0613", "gpt-4-0314"],
        "attributes": {
          "max_output": 8192,
          "context": 8192,
        }
      },
      "gpt-4-turbo": {
        "model_id": "gpt-4-turbo-preview",
        "variants": ["gpt-4-turbo-2024-04-09", "gpt-4-turbo-preview", "gpt-4-0125-preview", "gpt-4-1106-preview"],
        "attributes": {
          "max_output": 4096,
          "context": 128000,
        }
      }
    }
  },
  "anthropic": {
    "class": AnthropicTextModel,
    "inputs": ["text"],
    "outputs": ["text"],
    "models": {
      "claude-3-5-sonnet-20240620": {
        "model_id": "claude-3-sonnet-20240620",
        "variants": [],
        "attributes": {
          "max_output": 8192,
          "context": 200000,
        }
      }
    }
  },
  # "runpod": {
  #   "class": RunpodTextModel,
  #   "inputs": ["text"],
  #   "outputs": ["text"],
  #   "models": {
  #     "qwen2.5-72b-instruct": {
  #       "model_id": "qwen2.5-72b-instruct",
  #       "variants": [],
  #       "attributes": {
  #         "max_output": 8192,
  #         "context": 131072,
  #       }
  #     }
  #   }
  # },
  "local-minicpm3-4b": {
    "class": MiniCPM3_4B_LocalModel,
    "inputs": ["text"],
    "outputs": ["text"],
    "models": {
      "minicpm3-4b": {
        "model_id": "minicpm3-4b",
        "variants": [],
        "attributes": {
          "max_output": 1024,
          "context": 32000,
        }
      }
    }
  },
  "local-qwen2.5-32b-instruct": {
    "class": Qwen2p5_32B_InstructLocalModel,
    "inputs": ["text"],
    "outputs": ["text"],
    "models": {
      "qwen2.5-32b-instruct": {
        "model_id": "qwen2.5-32b-instruct",
        "variants": [],
        "attributes": {
          "max_output": 8192,
          "context": 131072,
        }
      }
    }
  },
  "openrouter": {
    "class": OpenRouterTextModel,
    "inputs": ["text"],
    "outputs": ["text"],
    "models": {
      "gpt-3.5-turbo": {
        "model_id": "openai/gpt-3.5-turbo",
        "variants": ["openai/gpt-3.5-turbo-0125", "openai/gpt-3.5-turbo-1106"],
        "attributes": {
          "max_output": 4096,
          "context": 16385,
        }
      },
      "gpt-4": {
        "model_id": "openai/gpt-4",
        "variants": ["openai/gpt-4-0613", "openai/gpt-4-0314"],
        "attributes": {
          "max_output": 8192,
          "context": 8192,
        }
      },
      "gpt-4-turbo": {
        "model_id": "openai/gpt-4-turbo-preview",
        "variants": ["openai/gpt-4-turbo-preview"],
        "attributes": {
          "max_output": 4096,
          "context": 128000,
        }
      },
      "claude-3-5-sonnet-20240620": {
        "model_id": "anthropic/claude-3-sonnet-20240620",
        "variants": [],
        "attributes": {
          "max_output": 8192,
          "context": 200000,
        }
      },
      "qwen2.5-72b-instruct": {
        "model_id": "qwen/qwen1.5-72b-chat",
        "variants": [],
        "attributes": {
          "max_output": 8192,
          "context": 131072,
        }
      }
    }
  }
}



##################################################
#              MODEL DEFINITIONS                 #
##################################################
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
  "gpt-3.5-turbo": {
    "title": "GPT 3.5 Turbo",
    "description": "The latest GPT-3.5 Turbo model with higher accuracy at responding in requested formats and a fix for a bug which caused a text encoding issue for non-English language function calls.",
    "capabilities": ["ttt"],
    "training_data": "Up to September 2021",
  },
  "gpt-4": {
    "title": "GPT 4",
    "description": "Snapshot of gpt-4 from June 13th 2023 with improved function calling support.",
    "capabilities": ["ttt"],
    "training_data": "Up to September 2021",
  },
  "gpt-4-turbo": {
    "title": "GPT 4 Turbo",
    "description": "The latest GPT-4 Turbo model with vision capabilities. Vision requests can now use JSON mode and function calling.",
    "capabilities": ["ttt"],
    "training_data": "Up to December 2023",
  },
  "claude-3-5-sonnet-20240620": {
    "title": "Claude 3.5 Sonnet",
    "description": "Claude 3.5 Sonnet sets new industry benchmarks for graduate-level reasoning (GPQA), undergraduate-level knowledge (MMLU), and coding proficiency (HumanEval). It shows marked improvement in grasping nuance, humor, and complex instructions, and is exceptional at writing high-quality content with a natural, relatable tone.",
    "capabilities": ["ttt"],
    "training_data": "Up to April 2024",
  },
  "minicpm3-4b": {
    "title": "MiniCPM3-4B",
    "description": "MiniCPM3-4B is the 3rd generation of MiniCPM series with a 32k context window.",
    "capabilities": ["ttt"],
    "training_data": "Not specified",
  },
  "qwen2.5-32b-instruct": {
    "title": "Qwen2.5-32B-Instruct",
    "description": "Qwen2.5 is the latest series of Qwen large language models. For Qwen2.5, we release a number of base language models and instruction-tuned language models ranging from 0.5 to 72 billion parameters.",
    "capabilities": ["ttt"],
    "training_data": "Not specified",
  },
  "qwen2.5-72b-instruct": {
    "title": "Qwen2.5-72B-Instruct",
    "description": "Qwen2.5's largest model with 72B parameters. Features improved capabilities in coding, mathematics, instruction following, and multilingual support for over 29 languages. Specialized in generating structured outputs and long-form content.",
    "capabilities": ["ttt"],
    "training_data": "Not specified",
  },
}



##################################################
#            CAPABILITY ABBREVIATIONS            #
##################################################
# Maps short codes to their full capability names
abbreviations = {
  "ttt": "text-to-text",
  "tti": "text-to-image",
  "itt": "image-to-text",
  "tts": "text-to-speech",
  "stt": "speech-to-text",
  "tta": "text-to-audio",
  "llm": "large-language-model",
  "slm": "small-language-model"
}



##################################################
#               INPUT/OUTPUT TYPES               #
##################################################
# Maps content types to their supported file extensions
types = {
  "text": ["txt"],
  "text-vision": ["txt", "png", "jpg"],
  "image": ["png", "jpg"],
}
