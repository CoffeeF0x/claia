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
  def get_model_definitions(self) -> Dict[str, ModelDefinition]:
    """Get Anthropic model definitions."""
    return {
      "claude-3-opus": ModelDefinition(
        title="Claude 3 Opus",
        aliases=["claude3", "opus"],
        company="Anthropic",
        deployments=["api"],
        architectures=["anthropic"],
        description="Anthropic's most powerful model for complex tasks",
        context_length=200000,
        capabilities=["chat", "reasoning", "analysis", "vision"],
        license="Commercial",
        url="https://www.anthropic.com/claude"
      ),

      "claude-3-sonnet": ModelDefinition(
        title="Claude 3 Sonnet",
        aliases=["sonnet"],
        company="Anthropic",
        deployments=["api"],
        architectures=["anthropic"],
        description="Balanced model for most conversational tasks",
        context_length=200000,
        capabilities=["chat", "reasoning", "analysis", "vision"],
        license="Commercial",
        url="https://www.anthropic.com/claude"
      ),

      "claude-3-haiku": ModelDefinition(
        title="Claude 3 Haiku",
        aliases=["haiku"],
        company="Anthropic",
        deployments=["api"],
        architectures=["anthropic"],
        description="Fast and cost-effective model for simple tasks",
        context_length=200000,
        capabilities=["chat", "reasoning"],
        license="Commercial",
        url="https://www.anthropic.com/claude"
      )
    }
