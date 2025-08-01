"""
Anthropic model definitions plugin.

Provides definitions for Anthropic Claude models.
"""

import logging
from typing import Dict

# Internal dependencies
from ..hooks.definition import ModelDefinition


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                               CLASSES                                #
########################################################################
class AnthropicDefinitionsPlugin:
  """Anthropic model definitions plugin."""

  def get_model_definitions(self) -> Dict[str, ModelDefinition]:
    """Get Anthropic model definitions."""
    return {
      "claude-3-opus": ModelDefinition(
        name="claude-3-opus",
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
        name="claude-3-sonnet",
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
        name="claude-3-haiku",
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
