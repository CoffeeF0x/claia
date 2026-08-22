"""MiniMax model definitions."""

from typing import Dict

from .base import BaseDefinitionProvider
from .model_definition import ModelDefinition
from ..data.chunks import TextChunk
from ..decorators import definitions
from ..enums.data import ArtifactType
from ..data.models.conversation.message_sequence import MessageSequence


@definitions
@definitions.name("minimax")
@definitions.title("MiniMax Definitions")
@definitions.description("MiniMax models available through OpenRouter.")
class MiniMaxDefinitions(BaseDefinitionProvider):
  """MiniMax model definitions."""

  def get_definitions(self) -> Dict[str, ModelDefinition]:
    """Get MiniMax model definitions."""
    return {
      "minimax-m2.7": ModelDefinition(
        title="MiniMax M2.7",
        aliases=["minimax"],
        company="MiniMax",
        architectures=["openrouter"],
        description="Next-generation productivity and autonomous-agent model for multi-agent collaboration",
        context_length=204800,
        capabilities=["chat", "code", "reasoning", "tool_use", "agentic"],
        license="Open Weights",
        url="https://openrouter.ai/models/minimax/minimax-m2.7",
        identifiers={"openrouter": "minimax/minimax-m2.7"},
        inputs=[ArtifactType.TEXT, MessageSequence],
        outputs=[TextChunk],
      ),

      "minimax-m2.5": ModelDefinition(
        title="MiniMax M2.5",
        aliases=["minimax-m2-5"],
        company="MiniMax",
        architectures=["openrouter"],
        description="Productivity-focused model for real-world office and agent workflows",
        context_length=196608,
        capabilities=["chat", "code", "reasoning", "tool_use", "agentic"],
        license="Open Weights",
        url="https://openrouter.ai/models/minimax/minimax-m2.5",
        identifiers={"openrouter": "minimax/minimax-m2.5"},
        inputs=[ArtifactType.TEXT, MessageSequence],
        outputs=[TextChunk],
      ),

      "minimax-m2": ModelDefinition(
        title="MiniMax M2",
        aliases=None,
        company="MiniMax",
        architectures=["openrouter"],
        description="MoE model optimized for coding and agentic workflows",
        context_length=196608,
        capabilities=["chat", "code", "reasoning", "tool_use", "agentic"],
        license="Open Weights",
        url="https://openrouter.ai/models/minimax/minimax-m2",
        identifiers={"openrouter": "minimax/minimax-m2"},
        inputs=[ArtifactType.TEXT, MessageSequence],
        outputs=[TextChunk],
      ),

      "minimax-m1": ModelDefinition(
        title="MiniMax M1",
        aliases=None,
        company="MiniMax",
        architectures=["openrouter"],
        description="Large-scale MoE reasoning model with a 1M-token context window",
        context_length=1000000,
        capabilities=["chat", "code", "reasoning", "tool_use"],
        license="Open Weights",
        url="https://openrouter.ai/models/minimax/minimax-m1",
        identifiers={"openrouter": "minimax/minimax-m1"},
        inputs=[ArtifactType.TEXT, MessageSequence],
        outputs=[TextChunk],
      ),
    }
