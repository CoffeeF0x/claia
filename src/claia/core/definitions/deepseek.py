"""DeepSeek model definitions (OpenRouter)."""

from typing import Dict

from .base import BaseDefinitionProvider
from .model_definition import ModelDefinition
from ._openrouter import definition
from ..decorators import definitions


@definitions
@definitions.name("deepseek")
@definitions.title("DeepSeek Definitions")
@definitions.description("DeepSeek models available through OpenRouter.")
class DeepSeekDefinitions(BaseDefinitionProvider):
  """DeepSeek model definitions."""

  def get_definitions(self) -> Dict[str, ModelDefinition]:
    return {
      "deepseek-v4-pro": definition(
        title="DeepSeek V4 Pro",
        identifiers={"openrouter": "deepseek/deepseek-v4-pro"},
        company="DeepSeek",
        aliases=["deepseek-pro", "deepseek-v4"],
        description="Large DeepSeek V4 MoE reasoning and coding model with a 1M-token context window.",
        context_length=1000000,
        capabilities=["chat", "code", "reasoning", "tool_use"],
        license="Open Source",
      ),
      "deepseek-v4-flash": definition(
        title="DeepSeek V4 Flash",
        identifiers={"openrouter": "deepseek/deepseek-v4-flash"},
        company="DeepSeek",
        aliases=["deepseek-flash"],
        description="Efficiency-optimized DeepSeek V4 MoE model for fast, high-throughput reasoning and coding.",
        context_length=1000000,
        capabilities=["chat", "code", "reasoning", "tool_use"],
        license="Open Source",
      ),
      "deepseek-r1-0528": definition(
        title="DeepSeek R1 0528",
        identifiers={"openrouter": "deepseek/deepseek-r1-0528"},
        company="DeepSeek",
        aliases=["deepseek-r1", "r1"],
        description="Open reasoning model update with strong math, coding, and tool-use performance.",
        context_length=163840,
        capabilities=["chat", "code", "reasoning", "tool_use", "structured_outputs"],
        license="Open Source",
      ),
    }
