"""MiniMax model definitions (OpenRouter)."""

from typing import Dict

from .base import BaseDefinitionProvider
from .model_definition import ModelDefinition
from ._openrouter import definition
from ..decorators import definitions


@definitions
@definitions.name("minimax")
@definitions.title("MiniMax Definitions")
@definitions.description("MiniMax models available through OpenRouter.")
class MiniMaxDefinitions(BaseDefinitionProvider):
  """MiniMax model definitions."""

  def get_definitions(self) -> Dict[str, ModelDefinition]:
    return {
      "minimax-m2.7": definition(
        title="MiniMax M2.7",
        identifiers={"openrouter": "minimax/minimax-m2.7"},
        company="MiniMax",
        aliases=["minimax"],
        description="Next-generation productivity and autonomous-agent model for multi-agent collaboration.",
        context_length=204800,
        capabilities=["chat", "code", "reasoning", "tool_use", "agentic"],
        license="Open Weights",
      ),
      "minimax-m2.5": definition(
        title="MiniMax M2.5",
        identifiers={"openrouter": "minimax/minimax-m2.5"},
        company="MiniMax",
        aliases=["minimax-m2-5"],
        description="Productivity-focused model for real-world office and agent workflows.",
        context_length=196608,
        capabilities=["chat", "code", "reasoning", "tool_use", "agentic"],
        license="Open Weights",
      ),
      "minimax-m2": definition(
        title="MiniMax M2",
        identifiers={"openrouter": "minimax/minimax-m2"},
        company="MiniMax",
        description="MoE model optimized for coding and agentic workflows.",
        context_length=196608,
        capabilities=["chat", "code", "reasoning", "tool_use", "agentic"],
        license="Open Weights",
      ),
      "minimax-m1": definition(
        title="MiniMax M1",
        identifiers={"openrouter": "minimax/minimax-m1"},
        company="MiniMax",
        description="Large-scale MoE reasoning model with a 1M-token context window.",
        context_length=1000000,
        capabilities=["chat", "code", "reasoning", "tool_use"],
        license="Open Weights",
      ),
    }
