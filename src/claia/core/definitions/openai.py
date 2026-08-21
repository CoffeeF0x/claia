"""
OpenAI model definitions.

Provides definitions for OpenAI models.

Alias convention (Docker-style rolling tags):
  Model keys use the canonical model-version.patch format: gpt-5.5
  Aliases omit version/patch segments for rolling resolution:
    gpt          →  latest flagship
    gpt-mini     →  latest mini-class
    gpt-nano     →  latest nano-class

Only the newest model in a class carries the shorter rolling aliases.
Older releases carry no aliases — use the key directly to pin them.
"""

import logging
from typing import Dict

from .base import BaseDefinitionProvider
from .model_definition import ModelDefinition
from ..data.chunks import TextChunk
from ..decorators import definitions
from ..enums.data import ArtifactType
from ..data.models.conversation.message_sequence import MessageSequence

_CHAT = [ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequence]
_TEXT = [TextChunk]


logger = logging.getLogger(__name__)


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
      # GPT-5.5 Series — current frontier
      # ----------------------------------------------------------------
      "gpt-5.5": ModelDefinition(
        title="GPT-5.5",
        aliases=["gpt"],      # latest flagship
        company="OpenAI",
        deployments=["api"],
        architectures=["openai", "openrouter"],
        description="OpenAI's latest flagship model for complex production workflows, coding, and tool-heavy agents",
        context_length=1050000,
        capabilities=["chat", "code", "reasoning", "vision", "web_search", "computer_use", "file_search"],
        license="Commercial",
        url="https://platform.openai.com/docs/guides/latest-model",
        identifiers={"openai": "gpt-5.5", "openrouter": "openai/gpt-5.5"},
        inputs=_CHAT,
        outputs=_TEXT,
      ),

      # ----------------------------------------------------------------
      # GPT-5.4 Series (previous frontier)
      # ----------------------------------------------------------------
      "gpt-5.4": ModelDefinition(
        title="GPT-5.4",
        aliases=None,
        company="OpenAI",
        deployments=["api"],
        architectures=["openai", "openrouter"],
        description="OpenAI's flagship model for complex reasoning, coding, and professional workflows",
        context_length=1050000,
        capabilities=["chat", "code", "reasoning", "vision", "web_search", "computer_use", "file_search"],
        license="Commercial",
        url="https://platform.openai.com/docs/models/gpt-5.4",
        identifiers={"openai": "gpt-5.4-2026-03-05", "openrouter": "openai/gpt-5.4"},
        inputs=_CHAT,
        outputs=_TEXT,
      ),

      "gpt-5.4-mini": ModelDefinition(
        title="GPT-5.4 Mini",
        aliases=["gpt-mini"],      # latest mini
        company="OpenAI",
        deployments=["api"],
        architectures=["openai", "openrouter"],
        description="Strongest mini model for coding, computer use, and subagents at lower cost",
        context_length=400000,
        capabilities=["chat", "code", "reasoning", "vision", "web_search", "computer_use", "file_search"],
        license="Commercial",
        url="https://platform.openai.com/docs/models/gpt-5.4-mini",
        identifiers={"openai": "gpt-5.4-mini-2026-03-17", "openrouter": "openai/gpt-5.4-mini"},
        inputs=_CHAT,
        outputs=_TEXT,
      ),

      "gpt-5.4-nano": ModelDefinition(
        title="GPT-5.4 Nano",
        aliases=["gpt-nano"],      # latest nano
        company="OpenAI",
        deployments=["api"],
        architectures=["openai", "openrouter"],
        description="Cheapest GPT-5.4-class model for high-volume tasks",
        context_length=400000,
        capabilities=["chat", "code", "reasoning", "vision", "file_search"],
        license="Commercial",
        url="https://platform.openai.com/docs/models/gpt-5.4-nano",
        identifiers={"openai": "gpt-5.4-nano-2026-03-17", "openrouter": "openai/gpt-5.4-nano"},
        inputs=_CHAT,
        outputs=_TEXT,
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
        url="https://platform.openai.com/docs/models/gpt-5",
        identifiers={"openai": "gpt-5-2025-08-07", "openrouter": "openai/gpt-5"},
        inputs=_CHAT,
        outputs=_TEXT,
      ),

      # ----------------------------------------------------------------
      # GPT-4o Series (still available)
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
        url="https://platform.openai.com/docs/models/gpt-4o",
        identifiers={"openai": "gpt-4o", "openrouter": "openai/gpt-4o"},
        inputs=_CHAT,
        outputs=_TEXT,
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
        url="https://platform.openai.com/docs/models/gpt-4o-mini",
        identifiers={"openai": "gpt-4o-mini", "openrouter": "openai/gpt-4o-mini"},
        inputs=_CHAT,
        outputs=_TEXT,
      ),
    }
