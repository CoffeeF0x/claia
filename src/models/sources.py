# External dependencies

# Internal dependencies
from models.api.openai import OpenAIModel
from models.api.runpod import RunpodModel
from models.api.anthropic import AnthropicModel
from models.api.openrouter import OpenRouterModel
from models.transformers import TransformersModel
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