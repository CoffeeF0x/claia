"""Meta Llama model definitions."""

from typing import Dict

from .base import BaseDefinitionProvider
from .model_definition import ModelDefinition
from ..data.chunks import TextChunk
from ..decorators import definitions
from ..enums.data import ArtifactType
from ..data.models.conversation.message_sequence import MessageSequence

_CHAT = [ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequence]
_TEXT = [TextChunk]


@definitions
@definitions.name("meta")
@definitions.title("Meta Definitions")
@definitions.description("Meta Llama models available through OpenRouter.")
class MetaDefinitions(BaseDefinitionProvider):
  """Meta Llama model definitions."""

  def get_definitions(self) -> Dict[str, ModelDefinition]:
    """Get Meta Llama model definitions."""
    return {
      "llama-4-maverick": ModelDefinition(
        title="Llama 4 Maverick",
        aliases=["llama-maverick", "llama-4", "llama"],
        company="Meta",
        deployments=["api"],
        architectures=["openrouter"],
        description="Large multimodal MoE model with broad multilingual text and code capabilities",
        context_length=1000000,
        capabilities=["chat", "code", "reasoning", "vision", "multilingual"],
        license="Llama 4 Community License",
        url="https://openrouter.ai/models/meta-llama/llama-4-maverick",
        identifiers={"openrouter": "meta-llama/llama-4-maverick"},
        inputs=_CHAT,
        outputs=_TEXT,
      ),

      "llama-4-scout": ModelDefinition(
        title="Llama 4 Scout",
        aliases=["llama-scout"],
        company="Meta",
        deployments=["api"],
        architectures=["openrouter"],
        description="Multimodal MoE model with an extremely long context window",
        context_length=10000000,
        capabilities=["chat", "code", "vision", "multilingual"],
        license="Llama 4 Community License",
        url="https://openrouter.ai/models/meta-llama/llama-4-scout",
        identifiers={"openrouter": "meta-llama/llama-4-scout"},
        inputs=_CHAT,
        outputs=_TEXT,
      ),
    }
