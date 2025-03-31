# External dependencies

# Internal dependencies
from .api.openai import OpenAIModel
from .api.runpod import RunpodModel
from .api.anthropic import AnthropicModel
from .api.openrouter import OpenRouterModel
from .transformers import TransformersModel, Gemma3Model, DiffusionModel
from .remote.vllm import VLLMModel



########################################################################
#                         MODEL SOURCE MAPPING                         #
########################################################################
# Maps source identifiers to their implementation classes
sources = {
  "openai": OpenAIModel,
  "anthropic": AnthropicModel,
  "transformers": TransformersModel,
  "openrouter": OpenRouterModel,
  "vllm": VLLMModel
}


########################################################################
#                    TRANSFORMERS MODEL MAPPING                        #
########################################################################
# Maps model families to their specialized implementation classes
# Used instead of class_map_overrides in model definitions
transformers_models = {
  # Model family prefix : implementation class
  "gemma-3": Gemma3Model,
  "stable-diffusion": DiffusionModel,
  # Add more specialized transformer model implementations here
  # "llama-3": Llama3Model,
  # "phi-3": Phi3Model,
}