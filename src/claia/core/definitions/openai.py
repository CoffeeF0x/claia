"""
OpenAI model definitions plugin.

Provides definitions for OpenAI models including GPT-4, GPT-3.5-turbo, etc.
"""

import logging
import pluggy
from typing import Dict

# Internal dependencies
from .model_definition import ModelDefinition


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)
hookimpl = pluggy.HookimplMarker("claia_definitions")


########################################################################
#                               CLASSES                                #
########################################################################
class OpenAIDefinitionsPlugin:
  """OpenAI model definitions plugin."""

  @hookimpl
  def get_definitions(self) -> Dict[str, ModelDefinition]:
    """Get OpenAI model definitions."""
    return {
      "gpt-4": ModelDefinition(
        title="GPT-4",
        company="OpenAI",
        deployments=["api"],
        architectures=["openai"],
        description="OpenAI's most advanced model for complex reasoning tasks",
        parameters="175B+",
        context_length=8192,
        capabilities=["chat", "code", "reasoning"],
        license="Commercial",
        url="https://openai.com/gpt-4"
      ),

      "gpt-4-turbo": ModelDefinition(
        title="GPT-4 Turbo",
        aliases=["gpt4-turbo"],
        company="OpenAI",
        deployments=["api"],
        architectures=["openai"],
        description="Faster and more efficient version of GPT-4",
        parameters="175B+",
        context_length=128000,
        capabilities=["chat", "code", "reasoning", "vision"],
        license="Commercial",
        url="https://openai.com/gpt-4"
      ),

      "gpt-3.5-turbo": ModelDefinition(
        title="GPT-3.5 Turbo",
        aliases=["gpt35", "gpt3.5"],
        company="OpenAI",
        deployments=["api"],
        architectures=["openai"],
        description="Fast and efficient model for most conversational tasks",
        parameters="175B",
        context_length=4096,
        capabilities=["chat", "code"],
        license="Commercial",
        url="https://openai.com/gpt-3-5"
      ),

      "gpt-3.5-turbo-16k": ModelDefinition(
        title="GPT-3.5 Turbo 16K",
        company="OpenAI",
        deployments=["api"],
        architectures=["openai"],
        description="GPT-3.5 Turbo with extended context length",
        parameters="175B",
        context_length=16384,
        capabilities=["chat", "code"],
        license="Commercial",
        url="https://openai.com/gpt-3-5"
      ),

      "gpt-4o": ModelDefinition(
        title="GPT-4o",
        aliases=["gpt4o"],
        company="OpenAI",
        deployments=["api"],
        architectures=["openai"],
        description="OpenAI's flagship multimodal model with vision and advanced reasoning",
        parameters="200B+",
        context_length=128000,
        capabilities=["chat", "code", "reasoning", "vision"],
        license="Commercial",
        url="https://openai.com/gpt-4o"
      ),

      "gpt-4o-mini": ModelDefinition(
        title="GPT-4o Mini",
        aliases=["gpt4o-mini"],
        company="OpenAI",
        deployments=["api"],
        architectures=["openai"],
        description="Smaller, faster, and more affordable GPT-4o variant",
        parameters="8B+",
        context_length=128000,
        capabilities=["chat", "code", "vision"],
        license="Commercial",
        url="https://openai.com/gpt-4o-mini"
      )
    }
