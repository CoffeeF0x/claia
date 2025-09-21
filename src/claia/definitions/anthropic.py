"""
Anthropic model definitions plugin.

Provides definitions for Anthropic Claude models.
"""

import logging
import pluggy
from typing import Dict

# Internal dependencies
from ..hooks.definition import ModelDefinition


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
      # Claude 4 Models
      "claude-opus-4-1": ModelDefinition(
        title="Claude Opus 4.1",
        aliases=["claude4", "opus-4.1", "claude-opus-4.1"],
        company="Anthropic",
        deployments=["api"],
        architectures=["anthropic"],
        description="Anthropic's most capable model with highest intelligence",
        context_length=200000,
        # max_output_tokens=32000,
        capabilities=["chat", "reasoning", "analysis", "vision", "extended_thinking", "priority_tier"],
        license="Commercial",
        url="https://www.anthropic.com/claude",
        identifiers={"anthropic": "claude-opus-4-1-20250805"}
      ),

      "claude-opus-4": ModelDefinition(
        title="Claude Opus 4",
        aliases=["opus-4", "claude-opus-4"],
        company="Anthropic",
        deployments=["api"],
        architectures=["anthropic"],
        description="Previous flagship model with very high intelligence",
        context_length=200000,
        # max_output_tokens=32000,
        capabilities=["chat", "reasoning", "analysis", "vision", "extended_thinking", "priority_tier"],
        license="Commercial",
        url="https://www.anthropic.com/claude",
        identifiers={"anthropic": "claude-opus-4-20250514"}
      ),

      "claude-sonnet-4": ModelDefinition(
        title="Claude Sonnet 4",
        aliases=["sonnet-4", "claude-sonnet-4"],
        company="Anthropic",
        deployments=["api"],
        architectures=["anthropic"],
        description="High-performance model with balanced intelligence and speed",
        context_length=200000,
        # max_output_tokens=64000,
        capabilities=["chat", "reasoning", "analysis", "vision", "extended_thinking", "priority_tier"],
        license="Commercial",
        url="https://www.anthropic.com/claude",
        identifiers={"anthropic": "claude-sonnet-4-20250514"}
      ),

      # Claude 3.7 Models
      "claude-3-7-sonnet": ModelDefinition(
        title="Claude Sonnet 3.7",
        aliases=["sonnet-3.7", "claude-sonnet-3.7"],
        company="Anthropic",
        deployments=["api"],
        architectures=["anthropic"],
        description="High-performance model with early extended thinking support",
        context_length=200000,
        # max_output_tokens=64000,
        capabilities=["chat", "reasoning", "analysis", "vision", "extended_thinking", "priority_tier"],
        license="Commercial",
        url="https://www.anthropic.com/claude",
        identifiers={"anthropic": "claude-sonnet-3-7-20250219"}
      ),

      # Claude 3.5 Models
      "claude-3-5-haiku": ModelDefinition(
        title="Claude Haiku 3.5",
        aliases=["haiku-3.5", "claude-haiku-3.5"],
        company="Anthropic",
        deployments=["api"],
        architectures=["anthropic"],
        description="Fastest model with intelligence at blazing speeds",
        context_length=200000,
        # max_output_tokens=8192,
        capabilities=["chat", "reasoning", "analysis", "vision", "priority_tier"],
        license="Commercial",
        url="https://www.anthropic.com/claude",
        identifiers={"anthropic": "claude-3-5-haiku-20241022"}
      ),

      # Claude 3 Models
      "claude-3-haiku": ModelDefinition(
        title="Claude Haiku 3",
        aliases=["haiku", "claude-3-haiku"],
        company="Anthropic",
        deployments=["api"],
        architectures=["anthropic"],
        description="Fast and compact model for near-instant responsiveness",
        context_length=200000,
        # max_output_tokens=4096,
        capabilities=["chat", "reasoning", "analysis", "vision"],
        license="Commercial",
        url="https://www.anthropic.com/claude",
        identifiers={"anthropic": "claude-3-haiku-20240307"}
      ),
    }
