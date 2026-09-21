"""MiniMax model definitions."""

from typing import Dict

from .base import BaseDefinitionProvider
from .model_definition import ModelDefinition
from ..data.chunks import TextChunk, ToolChunk
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
      "minimax-m3": ModelDefinition(
        title="MiniMax M3",
        aliases=["minimax"],
        company="MiniMax",
        architectures=["openrouter"],
        description="Multimodal foundation model for long-horizon agentic work and coding",
        context_length=1048576,
        capabilities=["chat", "code", "reasoning", "vision", "tool_use", "agentic"],
        license="Open Weights",
        url="https://openrouter.ai/models/minimax/minimax-m3",
        identifiers={"openrouter": "minimax/minimax-m3"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequence],
        outputs=[TextChunk, ToolChunk],
      ),

      "minimax-m2.7": ModelDefinition(
        title="MiniMax M2.7",
        aliases=["minimax-m2-7"],
        company="MiniMax",
        architectures=["openrouter"],
        description="Previous-generation productivity and autonomous-agent model for multi-agent collaboration",
        context_length=204800,
        capabilities=["chat", "code", "reasoning", "tool_use", "agentic"],
        license="Open Weights",
        url="https://openrouter.ai/models/minimax/minimax-m2.7",
        identifiers={"openrouter": "minimax/minimax-m2.7"},
        inputs=[ArtifactType.TEXT, MessageSequence],
        outputs=[TextChunk, ToolChunk],
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
        outputs=[TextChunk, ToolChunk],
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
        outputs=[TextChunk, ToolChunk],
      ),
    }
