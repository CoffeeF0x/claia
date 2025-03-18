# External dependencies

# Internal dependencies
from models.api.openai import OpenAIModel
from models.api.runpod import RunpodModel
from models.api.anthropic import AnthropicModel
from models.api.openrouter import OpenRouterModel
from models.transformers import TransformersModel, Gemma3Model
from models.remote.vllm import VLLMModel



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
  # Add more specialized transformer model implementations here
  # "llama-3": Llama3Model,
  # "phi-3": Phi3Model,
}