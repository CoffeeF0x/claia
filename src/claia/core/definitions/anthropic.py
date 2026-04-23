"""
Anthropic model definitions plugin.

Provides definitions for Anthropic Claude models.

Alias convention (Docker-style rolling tags):
  Model keys use all-dashes:  claude-opus-4-7   (canonical key, pinned)
  Aliases use model-version.patch with a dot:
    claude-opus-4.7  / opus-4.7   →  exact pinned aliases
    claude-opus-4    / opus-4     →  latest 4.x (minor omitted)
    claude-opus      / opus       →  latest of tier (version omitted)

Only the newest model in a series carries the shorter rolling aliases.
Older releases carry only their exact versioned aliases.

API identifier notes:
  Some models use a clean name as the API ID (claude-opus-4-7, claude-sonnet-4-6,
  claude-opus-4-6). Others use a date-stamped snapshot ID. Always check the
  identifiers field — it holds the value sent to the Anthropic API.
"""

import logging
import pluggy
from typing import Dict

# Internal dependencies
from .model_definition import ModelDefinition
from ..modality import Modality


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)
hookimpl = pluggy.HookimplMarker("claia_definitions")


########################################################################
#                               CLASSES                                #
########################################################################
class AnthropicDefinitionsPlugin:
  """Anthropic model definitions plugin."""

  @hookimpl
  def get_definitions(self) -> Dict[str, ModelDefinition]:
    """Get Anthropic model definitions."""
    return {
      # ----------------------------------------------------------------
      # Claude Opus  (newest → carries all rolling aliases)
      # ----------------------------------------------------------------
      "claude-opus-4-7": ModelDefinition(
        title="Claude Opus 4.7",
        aliases=["opus-4.7", "claude-opus-4.7",   # exact pinned
                 "claude-opus-4", "opus-4",         # latest 4.x
                 "claude-opus", "opus"],             # latest tier
        company="Anthropic",
        deployments=["api"],
        architectures=["anthropic"],
        description="Most capable model for complex reasoning and agentic coding",
        context_length=1000000,
        capabilities=["chat", "reasoning", "analysis", "vision", "adaptive_thinking", "computer_use"],
        license="Commercial",
        url="https://www.anthropic.com/claude",
        identifiers={"anthropic": "claude-opus-4-7"},
        input_modalities=[Modality.TEXT, Modality.IMAGE],
        output_modalities=[Modality.TEXT],
      ),

      "claude-opus-4-6": ModelDefinition(
        title="Claude Opus 4.6",
        aliases=["opus-4.6", "claude-opus-4.6"],
        company="Anthropic",
        deployments=["api"],
        architectures=["anthropic"],
        description="Highly capable model for complex agentic tasks and long-horizon work",
        context_length=1000000,
        capabilities=["chat", "reasoning", "analysis", "vision", "extended_thinking", "computer_use"],
        license="Commercial",
        url="https://www.anthropic.com/claude",
        identifiers={"anthropic": "claude-opus-4-6"},
        input_modalities=[Modality.TEXT, Modality.IMAGE],
        output_modalities=[Modality.TEXT],
      ),

      "claude-opus-4-5": ModelDefinition(
        title="Claude Opus 4.5",
        aliases=["opus-4.5", "claude-opus-4.5"],
        company="Anthropic",
        deployments=["api"],
        architectures=["anthropic"],
        description="Intelligent model for complex specialized tasks and professional software engineering",
        context_length=200000,
        capabilities=["chat", "reasoning", "analysis", "vision", "extended_thinking", "computer_use"],
        license="Commercial",
        url="https://www.anthropic.com/claude",
        identifiers={"anthropic": "claude-opus-4-5-20251101"},
        input_modalities=[Modality.TEXT, Modality.IMAGE],
        output_modalities=[Modality.TEXT],
      ),

      "claude-opus-4-1": ModelDefinition(
        title="Claude Opus 4.1",
        aliases=["opus-4.1", "claude-opus-4.1"],
        company="Anthropic",
        deployments=["api"],
        architectures=["anthropic"],
        description="Incremental update to Claude Opus 4 with enhanced capabilities",
        context_length=200000,
        capabilities=["chat", "reasoning", "analysis", "vision", "extended_thinking"],
        license="Commercial",
        url="https://www.anthropic.com/claude",
        identifiers={"anthropic": "claude-opus-4-1-20250805"},
        input_modalities=[Modality.TEXT, Modality.IMAGE],
        output_modalities=[Modality.TEXT],
      ),

      "claude-opus-4-0": ModelDefinition(
        title="Claude Opus 4.0",
        aliases=["opus-4.0", "claude-opus-4.0"],
        company="Anthropic",
        deployments=["api"],
        architectures=["anthropic"],
        description="[Deprecated] Original Claude Opus 4 — retiring June 15, 2026",
        context_length=200000,
        capabilities=["chat", "reasoning", "analysis", "vision", "extended_thinking"],
        license="Commercial",
        url="https://www.anthropic.com/claude",
        identifiers={"anthropic": "claude-opus-4-20250514"},
        input_modalities=[Modality.TEXT, Modality.IMAGE],
        output_modalities=[Modality.TEXT],
      ),

      # ----------------------------------------------------------------
      # Claude Sonnet  (newest → carries all rolling aliases)
      # ----------------------------------------------------------------
      "claude-sonnet-4-6": ModelDefinition(
        title="Claude Sonnet 4.6",
        aliases=["sonnet-4.6", "claude-sonnet-4.6",   # exact pinned
                 "claude-sonnet-4", "sonnet-4",         # latest 4.x
                 "claude-sonnet", "sonnet"],             # latest tier
        company="Anthropic",
        deployments=["api"],
        architectures=["anthropic"],
        description="Best balance of speed and intelligence for everyday and production use",
        context_length=1000000,
        capabilities=["chat", "reasoning", "analysis", "vision", "extended_thinking", "adaptive_thinking"],
        license="Commercial",
        url="https://www.anthropic.com/claude",
        identifiers={"anthropic": "claude-sonnet-4-6"},
        input_modalities=[Modality.TEXT, Modality.IMAGE],
        output_modalities=[Modality.TEXT],
      ),

      "claude-sonnet-4-5": ModelDefinition(
        title="Claude Sonnet 4.5",
        aliases=["sonnet-4.5", "claude-sonnet-4.5"],
        company="Anthropic",
        deployments=["api"],
        architectures=["anthropic"],
        description="High-intelligence model for complex agents and coding",
        context_length=200000,
        capabilities=["chat", "reasoning", "analysis", "vision", "extended_thinking"],
        license="Commercial",
        url="https://www.anthropic.com/claude",
        identifiers={"anthropic": "claude-sonnet-4-5-20250929"},
        input_modalities=[Modality.TEXT, Modality.IMAGE],
        output_modalities=[Modality.TEXT],
      ),

      "claude-sonnet-4-0": ModelDefinition(
        title="Claude Sonnet 4.0",
        aliases=["sonnet-4.0", "claude-sonnet-4.0"],
        company="Anthropic",
        deployments=["api"],
        architectures=["anthropic"],
        description="[Deprecated] Original Claude Sonnet 4 — retiring June 15, 2026",
        context_length=200000,
        capabilities=["chat", "reasoning", "analysis", "vision", "extended_thinking"],
        license="Commercial",
        url="https://www.anthropic.com/claude",
        identifiers={"anthropic": "claude-sonnet-4-20250514"},
        input_modalities=[Modality.TEXT, Modality.IMAGE],
        output_modalities=[Modality.TEXT],
      ),

      # ----------------------------------------------------------------
      # Claude Haiku  (newest → carries all rolling aliases)
      # ----------------------------------------------------------------
      "claude-haiku-4-5": ModelDefinition(
        title="Claude Haiku 4.5",
        aliases=["haiku-4.5", "claude-haiku-4.5",   # exact pinned
                 "claude-haiku-4", "haiku-4",         # latest 4.x
                 "claude-haiku", "haiku"],             # latest tier
        company="Anthropic",
        deployments=["api"],
        architectures=["anthropic"],
        description="Fastest model with near-frontier performance for real-time and high-volume use",
        context_length=200000,
        capabilities=["chat", "reasoning", "analysis", "vision", "extended_thinking"],
        license="Commercial",
        url="https://www.anthropic.com/claude",
        identifiers={"anthropic": "claude-haiku-4-5-20251001"},
        input_modalities=[Modality.TEXT, Modality.IMAGE],
        output_modalities=[Modality.TEXT],
      ),
    }
