"""Meta Llama model definitions (OpenRouter)."""

from typing import Dict

from .base import BaseDefinitionProvider
from .model_definition import ModelDefinition
from ._openrouter import VISION, definition
from ..decorators import definitions


@definitions
@definitions.name("meta")
@definitions.title("Meta Definitions")
@definitions.description("Meta Llama models available through OpenRouter.")
class MetaDefinitions(BaseDefinitionProvider):
  """Meta Llama model definitions."""

  def get_definitions(self) -> Dict[str, ModelDefinition]:
    return {
      "llama-4-maverick": definition(
        title="Llama 4 Maverick",
        provider_id="meta-llama/llama-4-maverick",
        company="Meta",
        aliases=["llama-maverick", "llama-4", "llama"],
        description="Large multimodal MoE model with broad multilingual text and code capabilities.",
        context_length=1000000,
        capabilities=["chat", "code", "reasoning", "vision", "multilingual"],
        inputs=VISION,
        license="Llama 4 Community License",
      ),
      "llama-4-scout": definition(
        title="Llama 4 Scout",
        provider_id="meta-llama/llama-4-scout",
        company="Meta",
        aliases=["llama-scout"],
        description="Multimodal MoE model with an extremely long context window.",
        context_length=10000000,
        capabilities=["chat", "code", "vision", "multilingual"],
        inputs=VISION,
        license="Llama 4 Community License",
      ),
    }
