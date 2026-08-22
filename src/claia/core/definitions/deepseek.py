"""DeepSeek model definitions."""

from typing import Dict

from .base import BaseDefinitionProvider
from .model_definition import ModelDefinition
from ..data.chunks import TextChunk
from ..decorators import definitions
from ..enums.data import ArtifactType
from ..data.models.conversation.message_sequence import MessageSequence

_PROMPT = [ArtifactType.TEXT, MessageSequence]
_TEXT = [TextChunk]


@definitions
@definitions.name("deepseek")
@definitions.title("DeepSeek Definitions")
@definitions.description("DeepSeek models available through OpenRouter.")
class DeepSeekDefinitions(BaseDefinitionProvider):
  """DeepSeek model definitions."""

  def get_definitions(self) -> Dict[str, ModelDefinition]:
    """Get DeepSeek model definitions."""
    return {
      "deepseek-v4-pro": ModelDefinition(
        title="DeepSeek V4 Pro",
        aliases=["deepseek-pro", "deepseek-v4"],
        company="DeepSeek",
        deployments=["api"],
        architectures=["openrouter"],
        description="Large DeepSeek V4 MoE reasoning and coding model with a 1M-token context window",
        context_length=1000000,
        capabilities=["chat", "code", "reasoning", "tool_use"],
        license="Open Source",
        url="https://openrouter.ai/models/deepseek/deepseek-v4-pro",
        identifiers={"openrouter": "deepseek/deepseek-v4-pro"},
        inputs=_PROMPT,
        outputs=_TEXT,
      ),

      "deepseek-v4-flash": ModelDefinition(
        title="DeepSeek V4 Flash",
        aliases=["deepseek-flash"],
        company="DeepSeek",
        deployments=["api"],
        architectures=["openrouter"],
        description="Efficiency-optimized DeepSeek V4 MoE model for fast, high-throughput reasoning and coding",
        context_length=1000000,
        capabilities=["chat", "code", "reasoning", "tool_use"],
        license="Open Source",
        url="https://openrouter.ai/models/deepseek/deepseek-v4-flash",
        identifiers={"openrouter": "deepseek/deepseek-v4-flash"},
        inputs=_PROMPT,
        outputs=_TEXT,
      ),

      "deepseek-r1-0528": ModelDefinition(
        title="DeepSeek R1 0528",
        aliases=["deepseek-r1", "r1"],
        company="DeepSeek",
        deployments=["api"],
        architectures=["openrouter"],
        description="Open reasoning model update with strong math, coding, and tool-use performance",
        context_length=163840,
        capabilities=["chat", "code", "reasoning", "tool_use", "structured_outputs"],
        license="Open Source",
        url="https://openrouter.ai/models/deepseek/deepseek-r1-0528",
        identifiers={"openrouter": "deepseek/deepseek-r1-0528"},
        inputs=_PROMPT,
        outputs=_TEXT,
      ),
    }
