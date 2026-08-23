"""
Anthropic model definitions.

Alias convention (Docker-style rolling tags):
  Model keys use all-dashes:  claude-opus-5   (canonical key, pinned)
  Aliases use model-version.patch with a dot:
    claude-opus-4.8  / opus-4.8   →  exact pinned aliases
    claude-opus-4    / opus-4     →  latest 4.x (minor omitted)
    claude-opus      / opus       →  latest of tier (version omitted)

Only the newest model in a series carries the shorter rolling aliases.
Older releases carry only their exact versioned aliases.

API identifier notes:
  Claude 4.6+ IDs are dateless pinned snapshots (claude-opus-5,
  claude-sonnet-4-6). Earlier models use a date-stamped snapshot ID.
  Always check the identifiers field — it holds the value sent to
  the Anthropic API.
"""

from typing import Dict

from .base import BaseDefinitionProvider
from .model_definition import ModelDefinition
from ..data.chunks import TextChunk, ToolChunk
from ..decorators import definitions
from ..enums.data import ArtifactType
from ..data.models.conversation.message_sequence import MessageSequenceOrdered


@definitions
@definitions.name("anthropic")
@definitions.title("Anthropic Definitions")
@definitions.description("Provides definitions for Anthropic Claude models.")
class AnthropicDefinitions(BaseDefinitionProvider):
  """Anthropic model definitions."""

  def get_definitions(self) -> Dict[str, ModelDefinition]:
    """Get Anthropic model definitions."""
    return {
      # ----------------------------------------------------------------
      # Claude Fable
      # ----------------------------------------------------------------
      "claude-fable-5": ModelDefinition(
        title="Claude Fable 5",
        aliases=["fable-5", "claude-fable", "fable"],
        company="Anthropic",
        architectures=["anthropic", "openrouter"],
        description="Most capable widely released model for long-running agents",
        context_length=1000000,
        capabilities=["chat", "reasoning", "analysis", "vision", "adaptive_thinking"],
        license="Commercial",
        url="https://platform.claude.com/docs/en/about-claude/models/overview",
        identifiers={"anthropic": "claude-fable-5", "openrouter": "anthropic/claude-fable-5"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequenceOrdered],
        outputs=[TextChunk, ToolChunk],
      ),

      # ----------------------------------------------------------------
      # Claude Opus  (newest → carries all rolling aliases)
      # ----------------------------------------------------------------
      "claude-opus-5": ModelDefinition(
        title="Claude Opus 5",
        aliases=["opus-5", "claude-opus-5",
                 "claude-opus", "opus"],
        company="Anthropic",
        architectures=["anthropic", "openrouter"],
        description="Most capable model for complex agentic coding and enterprise work",
        context_length=1000000,
        capabilities=["chat", "reasoning", "analysis", "vision", "adaptive_thinking"],
        license="Commercial",
        url="https://platform.claude.com/docs/en/about-claude/models/overview",
        identifiers={"anthropic": "claude-opus-5", "openrouter": "anthropic/claude-opus-5"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequenceOrdered],
        outputs=[TextChunk, ToolChunk],
      ),

      "claude-opus-4-8": ModelDefinition(
        title="Claude Opus 4.8",
        aliases=["opus-4.8", "claude-opus-4.8",
                 "claude-opus-4", "opus-4"],
        company="Anthropic",
        architectures=["anthropic", "openrouter"],
        description="Previous Opus generation for complex reasoning and agentic coding",
        context_length=1000000,
        capabilities=["chat", "reasoning", "analysis", "vision", "adaptive_thinking"],
        license="Commercial",
        url="https://platform.claude.com/docs/en/about-claude/models/overview",
        identifiers={"anthropic": "claude-opus-4-8", "openrouter": "anthropic/claude-opus-4.8"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequenceOrdered],
        outputs=[TextChunk, ToolChunk],
      ),

      "claude-opus-4-7": ModelDefinition(
        title="Claude Opus 4.7",
        aliases=["opus-4.7", "claude-opus-4.7"],
        company="Anthropic",
        architectures=["anthropic", "openrouter"],
        description="Capable model for complex reasoning and agentic coding",
        context_length=1000000,
        capabilities=["chat", "reasoning", "analysis", "vision", "adaptive_thinking", "computer_use"],
        license="Commercial",
        url="https://platform.claude.com/docs/en/about-claude/models/overview",
        identifiers={"anthropic": "claude-opus-4-7", "openrouter": "anthropic/claude-opus-4.7"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequenceOrdered],
        outputs=[TextChunk, ToolChunk],
      ),

      "claude-opus-4-6": ModelDefinition(
        title="Claude Opus 4.6",
        aliases=["opus-4.6", "claude-opus-4.6"],
        company="Anthropic",
        architectures=["anthropic", "openrouter"],
        description="Highly capable model for complex agentic tasks and long-horizon work",
        context_length=1000000,
        capabilities=["chat", "reasoning", "analysis", "vision", "extended_thinking", "adaptive_thinking", "computer_use"],
        license="Commercial",
        url="https://platform.claude.com/docs/en/about-claude/models/overview",
        identifiers={"anthropic": "claude-opus-4-6", "openrouter": "anthropic/claude-opus-4.6"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequenceOrdered],
        outputs=[TextChunk, ToolChunk],
      ),

      "claude-opus-4-5": ModelDefinition(
        title="Claude Opus 4.5",
        aliases=["opus-4.5", "claude-opus-4.5"],
        company="Anthropic",
        architectures=["anthropic", "openrouter"],
        description="Intelligent model for complex specialized tasks and professional software engineering",
        context_length=200000,
        capabilities=["chat", "reasoning", "analysis", "vision", "extended_thinking", "computer_use"],
        license="Commercial",
        url="https://platform.claude.com/docs/en/about-claude/models/overview",
        identifiers={"anthropic": "claude-opus-4-5-20251101", "openrouter": "anthropic/claude-opus-4.5"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequenceOrdered],
        outputs=[TextChunk, ToolChunk],
      ),

      "claude-opus-4-1": ModelDefinition(
        title="Claude Opus 4.1",
        aliases=["opus-4.1", "claude-opus-4.1"],
        company="Anthropic",
        architectures=["anthropic", "openrouter"],
        description="Incremental update to Claude Opus 4 with enhanced capabilities",
        context_length=200000,
        capabilities=["chat", "reasoning", "analysis", "vision", "extended_thinking"],
        license="Commercial",
        url="https://platform.claude.com/docs/en/about-claude/models/overview",
        identifiers={"anthropic": "claude-opus-4-1-20250805", "openrouter": "anthropic/claude-opus-4.1"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequenceOrdered],
        outputs=[TextChunk, ToolChunk],
      ),

      # ----------------------------------------------------------------
      # Claude Sonnet  (newest → carries all rolling aliases)
      # ----------------------------------------------------------------
      "claude-sonnet-5": ModelDefinition(
        title="Claude Sonnet 5",
        aliases=["sonnet-5", "claude-sonnet-5",
                 "claude-sonnet", "sonnet"],
        company="Anthropic",
        architectures=["anthropic", "openrouter"],
        description="Best balance of speed and intelligence for everyday and production use",
        context_length=1000000,
        capabilities=["chat", "reasoning", "analysis", "vision", "adaptive_thinking"],
        license="Commercial",
        url="https://platform.claude.com/docs/en/about-claude/models/overview",
        identifiers={"anthropic": "claude-sonnet-5", "openrouter": "anthropic/claude-sonnet-5"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequenceOrdered],
        outputs=[TextChunk, ToolChunk],
      ),

      "claude-sonnet-4-6": ModelDefinition(
        title="Claude Sonnet 4.6",
        aliases=["sonnet-4.6", "claude-sonnet-4.6",
                 "claude-sonnet-4", "sonnet-4"],
        company="Anthropic",
        architectures=["anthropic", "openrouter"],
        description="Previous Sonnet generation for everyday and production use",
        context_length=1000000,
        capabilities=["chat", "reasoning", "analysis", "vision", "extended_thinking", "adaptive_thinking"],
        license="Commercial",
        url="https://platform.claude.com/docs/en/about-claude/models/overview",
        identifiers={"anthropic": "claude-sonnet-4-6", "openrouter": "anthropic/claude-sonnet-4.6"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequenceOrdered],
        outputs=[TextChunk, ToolChunk],
      ),

      "claude-sonnet-4-5": ModelDefinition(
        title="Claude Sonnet 4.5",
        aliases=["sonnet-4.5", "claude-sonnet-4.5"],
        company="Anthropic",
        architectures=["anthropic", "openrouter"],
        description="High-intelligence model for complex agents and coding",
        context_length=200000,
        capabilities=["chat", "reasoning", "analysis", "vision", "extended_thinking"],
        license="Commercial",
        url="https://platform.claude.com/docs/en/about-claude/models/overview",
        identifiers={"anthropic": "claude-sonnet-4-5-20250929", "openrouter": "anthropic/claude-sonnet-4.5"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequenceOrdered],
        outputs=[TextChunk, ToolChunk],
      ),

      # ----------------------------------------------------------------
      # Claude Haiku  (newest → carries all rolling aliases)
      # ----------------------------------------------------------------
      "claude-haiku-4-5": ModelDefinition(
        title="Claude Haiku 4.5",
        aliases=["haiku-4.5", "claude-haiku-4.5",
                 "claude-haiku-4", "haiku-4",
                 "claude-haiku", "haiku"],
        company="Anthropic",
        architectures=["anthropic", "openrouter"],
        description="Fastest model with near-frontier performance for real-time and high-volume use",
        context_length=200000,
        capabilities=["chat", "reasoning", "analysis", "vision", "extended_thinking"],
        license="Commercial",
        url="https://platform.claude.com/docs/en/about-claude/models/overview",
        identifiers={"anthropic": "claude-haiku-4-5-20251001", "openrouter": "anthropic/claude-haiku-4.5"},
        inputs=[ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequenceOrdered],
        outputs=[TextChunk, ToolChunk],
      ),
    }
