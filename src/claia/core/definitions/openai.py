"""
OpenAI model definitions.

Alias convention (Docker-style rolling tags):
  Model keys use the vendor id: gpt-5.6-sol
  Aliases omit version/class segments for rolling resolution:
    gpt          →  latest flagship
    gpt-5.6      →  latest in the 5.6 family

Only the newest model in a class carries the shorter rolling aliases.
Older releases carry no aliases — use the key directly to pin them.
"""

from typing import Dict

from .base import BaseDefinitionProvider
from .model_definition import ModelDefinition
from ..data.chunks import TextChunk
from ..decorators import definitions
from ..enums.data import ArtifactType
from ..data.models.conversation.message_sequence import MessageSequence


@definitions
@definitions.name("openai")
@definitions.title("OpenAI Definitions")
@definitions.description("Provides definitions for OpenAI models.")
class OpenAIDefinitions(BaseDefinitionProvider):
  """OpenAI model definitions."""

  def get_definitions(self) -> Dict[str, ModelDefinition]:
    """Get OpenAI model definitions."""
    return {
      # ----------------------------------------------------------------
      # GPT-5.6 Series — current frontier
      # ----------------------------------------------------------------
      "gpt-5.6-sol": ModelDefinition(
        title="GPT-5.6 Sol",
        aliases=["gpt", "gpt-5.6"],
        company="OpenAI",
        deployments=["api"],
        architectures=["openai", "openrouter"],
        description="Frontier model for complex reasoning, coding, and professional work",
        context_length=1050000,
        capabilities=["chat", "code", "reasoning", "vision", "web_search", "computer_use", "file_search"],
        license="Commercial",
        url="https://developers.openai.com/api/docs/models/gpt-5.6-sol",
        identifiers={"openai": "gpt-5.6-sol", "openrouter": "openai/gpt-5.6-sol"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequence],
        outputs=[TextChunk],
      ),

      "gpt-5.6-terra": ModelDefinition(
        title="GPT-5.6 Terra",
        aliases=["gpt-terra"],
        company="OpenAI",
        deployments=["api"],
        architectures=["openai", "openrouter"],
        description="GPT-5.6 model that balances intelligence and cost",
        context_length=1050000,
        capabilities=["chat", "code", "reasoning", "vision", "web_search", "computer_use", "file_search"],
        license="Commercial",
        url="https://developers.openai.com/api/docs/models/gpt-5.6-terra",
        identifiers={"openai": "gpt-5.6-terra", "openrouter": "openai/gpt-5.6-terra"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequence],
        outputs=[TextChunk],
      ),

      "gpt-5.6-luna": ModelDefinition(
        title="GPT-5.6 Luna",
        aliases=["gpt-luna"],
        company="OpenAI",
        deployments=["api"],
        architectures=["openai", "openrouter"],
        description="GPT-5.6 model optimized for cost-sensitive, high-volume workloads",
        context_length=1050000,
        capabilities=["chat", "code", "reasoning", "vision", "web_search", "computer_use", "file_search"],
        license="Commercial",
        url="https://developers.openai.com/api/docs/models/gpt-5.6-luna",
        identifiers={"openai": "gpt-5.6-luna", "openrouter": "openai/gpt-5.6-luna"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequence],
        outputs=[TextChunk],
      ),

      # ----------------------------------------------------------------
      # GPT-5.5
      # ----------------------------------------------------------------
      "gpt-5.5": ModelDefinition(
        title="GPT-5.5",
        aliases=None,
        company="OpenAI",
        deployments=["api"],
        architectures=["openai", "openrouter"],
        description="Previous frontier model for complex production workflows and tool-heavy agents",
        context_length=1050000,
        capabilities=["chat", "code", "reasoning", "vision", "web_search", "computer_use", "file_search"],
        license="Commercial",
        url="https://developers.openai.com/api/docs/models/gpt-5.5",
        identifiers={"openai": "gpt-5.5", "openrouter": "openai/gpt-5.5"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequence],
        outputs=[TextChunk],
      ),

      # ----------------------------------------------------------------
      # GPT-5.4 Series
      # ----------------------------------------------------------------
      "gpt-5.4": ModelDefinition(
        title="GPT-5.4",
        aliases=None,
        company="OpenAI",
        deployments=["api"],
        architectures=["openai", "openrouter"],
        description="Flagship model for complex reasoning, coding, and professional workflows",
        context_length=1050000,
        capabilities=["chat", "code", "reasoning", "vision", "web_search", "computer_use", "file_search"],
        license="Commercial",
        url="https://developers.openai.com/api/docs/models/gpt-5.4",
        identifiers={"openai": "gpt-5.4-2026-03-05", "openrouter": "openai/gpt-5.4"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequence],
        outputs=[TextChunk],
      ),

      "gpt-5.4-mini": ModelDefinition(
        title="GPT-5.4 Mini",
        aliases=None,
        company="OpenAI",
        deployments=["api"],
        architectures=["openai", "openrouter"],
        description="Strong mini model for coding, computer use, and subagents at lower cost",
        context_length=400000,
        capabilities=["chat", "code", "reasoning", "vision", "web_search", "computer_use", "file_search"],
        license="Commercial",
        url="https://developers.openai.com/api/docs/models/gpt-5.4-mini",
        identifiers={"openai": "gpt-5.4-mini-2026-03-17", "openrouter": "openai/gpt-5.4-mini"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequence],
        outputs=[TextChunk],
      ),

      "gpt-5.4-nano": ModelDefinition(
        title="GPT-5.4 Nano",
        aliases=None,
        company="OpenAI",
        deployments=["api"],
        architectures=["openai", "openrouter"],
        description="Cheapest GPT-5.4-class model for high-volume tasks",
        context_length=400000,
        capabilities=["chat", "code", "reasoning", "vision", "file_search"],
        license="Commercial",
        url="https://developers.openai.com/api/docs/models/gpt-5.4-nano",
        identifiers={"openai": "gpt-5.4-nano-2026-03-17", "openrouter": "openai/gpt-5.4-nano"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequence],
        outputs=[TextChunk],
      ),

      # ----------------------------------------------------------------
      # GPT-5 (August 2025)
      # ----------------------------------------------------------------
      "gpt-5": ModelDefinition(
        title="GPT-5",
        aliases=None,
        company="OpenAI",
        deployments=["api"],
        architectures=["openai", "openrouter"],
        description="Intelligent reasoning model for coding and agentic tasks",
        context_length=400000,
        capabilities=["chat", "code", "reasoning", "vision", "web_search", "file_search"],
        license="Commercial",
        url="https://developers.openai.com/api/docs/models/gpt-5",
        identifiers={"openai": "gpt-5-2025-08-07", "openrouter": "openai/gpt-5"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequence],
        outputs=[TextChunk],
      ),

      # ----------------------------------------------------------------
      # GPT-4o Series
      # ----------------------------------------------------------------
      "gpt-4o": ModelDefinition(
        title="GPT-4o",
        aliases=None,
        company="OpenAI",
        deployments=["api"],
        architectures=["openai", "openrouter"],
        description="Versatile multimodal model with vision and advanced reasoning",
        context_length=128000,
        capabilities=["chat", "code", "reasoning", "vision"],
        license="Commercial",
        url="https://developers.openai.com/api/docs/models/gpt-4o",
        identifiers={"openai": "gpt-4o", "openrouter": "openai/gpt-4o"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequence],
        outputs=[TextChunk],
      ),

      "gpt-4o-mini": ModelDefinition(
        title="GPT-4o Mini",
        aliases=None,
        company="OpenAI",
        deployments=["api"],
        architectures=["openai", "openrouter"],
        description="Smaller, faster, and more affordable GPT-4o variant",
        context_length=128000,
        capabilities=["chat", "code", "vision"],
        license="Commercial",
        url="https://developers.openai.com/api/docs/models/gpt-4o-mini",
        identifiers={"openai": "gpt-4o-mini", "openrouter": "openai/gpt-4o-mini"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequence],
        outputs=[TextChunk],
      ),
    }
