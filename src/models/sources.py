# External dependencies

# Internal dependencies
from models.api.openai import OpenAITextModel
from models.api.runpod import RunpodTextModel
from models.api.anthropic import AnthropicTextModel
from models.api.openrouter import OpenRouterTextModel
from models.transformers import TransformersTextModel
from models.remote.vllm import VLLMTextModel



########################################################################
#                         MODEL SOURCE MAPPING                         #
########################################################################
# Maps source identifiers to their implementation classes
sources = {
  "openai": OpenAITextModel,
  "anthropic": AnthropicTextModel,
  "transformers": TransformersTextModel,
  "openrouter": OpenRouterTextModel,
  "vllm": VLLMTextModel
}