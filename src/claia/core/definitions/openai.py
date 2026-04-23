"""
OpenAI model definitions plugin.

Provides definitions for OpenAI models.

Alias convention (Docker-style rolling tags):
  Model keys use the canonical model-version.patch format: gpt-5.4
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
from ..modality import Modality


logger = logging.getLogger(__name__)


class OpenAIDefinitionsPlugin(BaseDefinitionProvider):
  """OpenAI model definitions plugin."""

  def get_definitions(self) -> Dict[str, ModelDefinition]:
    """Get OpenAI model definitions."""
    return {
      # ----------------------------------------------------------------
      # GPT-5.4 Series — current frontier (March 2026)
      # ----------------------------------------------------------------
      "gpt-5.4": ModelDefinition(
        title="GPT-5.4",
        aliases=["gpt"],      # latest flagship
        company="OpenAI",
        deployments=["api"],
        architectures=["openai"],
        description="OpenAI's flagship model for complex reasoning, coding, and professional workflows",
        context_length=1050000,
        capabilities=["chat", "code", "reasoning", "vision", "web_search", "computer_use", "file_search"],
        license="Commercial",
        url="https://platform.openai.com/docs/models/gpt-5.4",
        identifiers={"openai": "gpt-5.4-2026-03-05"},
        input_modalities=[Modality.TEXT, Modality.IMAGE],
        output_modalities=[Modality.TEXT],
      ),

      "gpt-5.4-mini": ModelDefinition(
        title="GPT-5.4 Mini",
        aliases=["gpt-mini"],      # latest mini
        company="OpenAI",
        deployments=["api"],
        architectures=["openai"],
        description="Strongest mini model for coding, computer use, and subagents at lower cost",
        context_length=400000,
        capabilities=["chat", "code", "reasoning", "vision", "web_search", "computer_use", "file_search"],
        license="Commercial",
        url="https://platform.openai.com/docs/models/gpt-5.4-mini",
        identifiers={"openai": "gpt-5.4-mini-2026-03-17"},
        input_modalities=[Modality.TEXT, Modality.IMAGE],
        output_modalities=[Modality.TEXT],
      ),

      "gpt-5.4-nano": ModelDefinition(
        title="GPT-5.4 Nano",
        aliases=["gpt-nano"],      # latest nano
        company="OpenAI",
        deployments=["api"],
        architectures=["openai"],
        description="Cheapest GPT-5.4-class model for high-volume tasks",
        context_length=400000,
        capabilities=["chat", "code", "reasoning", "vision", "file_search"],
        license="Commercial",
        url="https://platform.openai.com/docs/models/gpt-5.4-nano",
        identifiers={"openai": "gpt-5.4-nano-2026-03-17"},
        input_modalities=[Modality.TEXT, Modality.IMAGE],
        output_modalities=[Modality.TEXT],
      ),

      # ----------------------------------------------------------------
      # GPT-5 (August 2025)
      # ----------------------------------------------------------------
      "gpt-5": ModelDefinition(
        title="GPT-5",
        aliases=None,
        company="OpenAI",
        deployments=["api"],
        architectures=["openai"],
        description="Intelligent reasoning model for coding and agentic tasks",
        context_length=400000,
        capabilities=["chat", "code", "reasoning", "vision", "web_search", "file_search"],
        license="Commercial",
        url="https://platform.openai.com/docs/models/gpt-5",
        identifiers={"openai": "gpt-5-2025-08-07"},
        input_modalities=[Modality.TEXT, Modality.IMAGE],
        output_modalities=[Modality.TEXT],
      ),

      # ----------------------------------------------------------------
      # GPT-4o Series (still available)
      # ----------------------------------------------------------------
      "gpt-4o": ModelDefinition(
        title="GPT-4o",
        aliases=None,
        company="OpenAI",
        deployments=["api"],
        architectures=["openai"],
        description="Versatile multimodal model with vision and advanced reasoning",
        context_length=128000,
        capabilities=["chat", "code", "reasoning", "vision"],
        license="Commercial",
        url="https://platform.openai.com/docs/models/gpt-4o",
        identifiers={"openai": "gpt-4o"},
        input_modalities=[Modality.TEXT, Modality.IMAGE],
        output_modalities=[Modality.TEXT],
      ),

      "gpt-4o-mini": ModelDefinition(
        title="GPT-4o Mini",
        aliases=None,
        company="OpenAI",
        deployments=["api"],
        architectures=["openai"],
        description="Smaller, faster, and more affordable GPT-4o variant",
        context_length=128000,
        capabilities=["chat", "code", "vision"],
        license="Commercial",
        url="https://platform.openai.com/docs/models/gpt-4o-mini",
        identifiers={"openai": "gpt-4o-mini"},
        input_modalities=[Modality.TEXT, Modality.IMAGE],
        output_modalities=[Modality.TEXT],
      ),
    }
