"""Moonshot AI / Kimi model definitions."""

from typing import Dict

from .base import BaseDefinitionProvider
from .model_definition import ModelDefinition
from ..data.chunks import TextChunk
from ..decorators import definitions
from ..enums.data import ArtifactType
from ..data.models.conversation.message_sequence import MessageSequence


@definitions
@definitions.name("moonshot")
@definitions.title("Moonshot AI Definitions")
@definitions.description("Moonshot AI / Kimi models available through OpenRouter.")
class MoonshotDefinitions(BaseDefinitionProvider):
  """Moonshot AI model definitions."""

  def get_definitions(self) -> Dict[str, ModelDefinition]:
    """Get Moonshot AI model definitions."""
    return {
      "kimi-k3": ModelDefinition(
        title="Kimi K3",
        aliases=["kimi", "kimi-k3"],
        company="Moonshot AI",
        architectures=["openrouter"],
        description="Open-weight multimodal reasoning model for long-horizon coding and knowledge work",
        context_length=1048576,
        capabilities=["chat", "code", "reasoning", "vision", "tool_use", "agentic"],
        license="Open Weights",
        url="https://openrouter.ai/models/moonshotai/kimi-k3",
        identifiers={"openrouter": "moonshotai/kimi-k3"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequence],
        outputs=[TextChunk],
      ),

      "kimi-k2.7-code": ModelDefinition(
        title="Kimi K2.7 Code",
        aliases=["kimi-k2.7", "kimi-code"],
        company="Moonshot AI",
        architectures=["openrouter"],
        description="Coding-focused multimodal MoE for long-horizon programming and agentic decomposition",
        context_length=262144,
        capabilities=["chat", "code", "reasoning", "vision", "tool_use", "agentic"],
        license="Open Weights",
        url="https://openrouter.ai/models/moonshotai/kimi-k2.7-code",
        identifiers={"openrouter": "moonshotai/kimi-k2.7-code"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequence],
        outputs=[TextChunk],
      ),

      "kimi-k2.6": ModelDefinition(
        title="Kimi K2.6",
        aliases=["kimi-k2", "kimi-k2-6"],
        company="Moonshot AI",
        architectures=["openrouter"],
        description="Multimodal model for long-horizon coding and multi-agent orchestration",
        context_length=256000,
        capabilities=["chat", "code", "reasoning", "vision", "tool_use", "agentic"],
        license="Open Weights",
        url="https://openrouter.ai/models/moonshotai/kimi-k2.6",
        identifiers={"openrouter": "moonshotai/kimi-k2.6"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequence],
        outputs=[TextChunk],
      ),

      "kimi-k2.5": ModelDefinition(
        title="Kimi K2.5",
        aliases=["kimi-k2-5"],
        company="Moonshot AI",
        architectures=["openrouter"],
        description="Multimodal Kimi K2 continuation with strong visual coding and agentic performance",
        context_length=262144,
        capabilities=["chat", "code", "reasoning", "vision", "tool_use", "agentic"],
        license="Open Weights",
        url="https://openrouter.ai/models/moonshotai/kimi-k2.5",
        identifiers={"openrouter": "moonshotai/kimi-k2.5"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequence],
        outputs=[TextChunk],
      ),

      "kimi-k2-thinking": ModelDefinition(
        title="Kimi K2 Thinking",
        aliases=["kimi-thinking"],
        company="Moonshot AI",
        architectures=["openrouter"],
        description="Open reasoning MoE model optimized for step-by-step reasoning, tool use, and long workflows",
        context_length=256000,
        capabilities=["chat", "code", "reasoning", "tool_use", "agentic"],
        license="Open Weights",
        url="https://openrouter.ai/models/moonshotai/kimi-k2-thinking",
        identifiers={"openrouter": "moonshotai/kimi-k2-thinking"},
        inputs=[ArtifactType.TEXT, MessageSequence],
        outputs=[TextChunk],
      ),
    }
