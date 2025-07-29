"""
Anthropic model plugin.

Provides Anthropic API-based models like Claude-3, Claude-2, etc.
"""

import logging
from typing import Dict, Any, List, Type

# Internal dependencies
from common.results import Result
from ..hooks.model_hooks import ModelInfo
from legacy.api.anthropic import AnthropicModel


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                              CONSTANTS                               #
########################################################################
# Available Anthropic models
ANTHROPIC_MODELS = {
  "claude-3-opus-20240229": {
    "name": "claude-3-opus-20240229",
    "title": "Claude 3 Opus",
    "model_type": "api",
    "provider": "anthropic"
  },
  "claude-3-sonnet-20240229": {
    "name": "claude-3-sonnet-20240229",
    "title": "Claude 3 Sonnet",
    "model_type": "api",
    "provider": "anthropic"
  },
  "claude-3-haiku-20240307": {
    "name": "claude-3-haiku-20240307",
    "title": "Claude 3 Haiku",
    "model_type": "api",
    "provider": "anthropic"
  },
  "claude-2.1": {
    "name": "claude-2.1",
    "title": "Claude 2.1",
    "model_type": "api",
    "provider": "anthropic"
  },
  "claude-2.0": {
    "name": "claude-2.0",
    "title": "Claude 2.0",
    "model_type": "api",
    "provider": "anthropic"
  }
}

# Model aliases
MODEL_ALIASES = {
  "anthropic": "claude-3-opus-20240229",
  "claude": "claude-3-opus-20240229",
  "claude-3": "claude-3-opus-20240229",
  "claude-opus": "claude-3-opus-20240229",
  "claude-sonnet": "claude-3-sonnet-20240229",
  "claude-haiku": "claude-3-haiku-20240307",
  "claude-2": "claude-2.1"
}


########################################################################
#                               CLASSES                                #
########################################################################
class AnthropicPlugin:
  """
  Anthropic model plugin providing Claude models via Anthropic API.
  """

  def get_supported_models(self) -> List[ModelInfo]:
    """Get list of supported Anthropic models."""
    models = []
    for model_id, model_data in ANTHROPIC_MODELS.items():
      models.append(ModelInfo(
        name=model_data["name"],
        title=model_data["title"],
        model_type=model_data["model_type"],
        provider=model_data["provider"],
        aliases=self._get_aliases_for_model(model_id)
      ))
    return models

  def get_model_class(self, model_name: str) -> Result[Type]:
    """Get the model class for the specified model."""
    try:
      # Check if model exists in our supported models
      if model_name not in ANTHROPIC_MODELS:
        return Result.fail(f"Unsupported Anthropic model: {model_name}")

      return Result(data=AnthropicModel)

    except Exception as e:
      logger.error(f"Error getting Anthropic model class for {model_name}: {str(e)}")
      return Result.fail(f"Failed to get model class: {str(e)}")

  def resolve_model_name(self, model_name: str) -> str:
    """Resolve model name from alias to canonical name."""
    return MODEL_ALIASES.get(model_name, model_name)

  def supports_specialized_loading(self, model_name: str) -> bool:
    """Check if model supports specialized loading."""
    # Anthropic models don't need specialized loading
    return False

  def _get_aliases_for_model(self, model_id: str) -> List[str]:
    """Get aliases that point to this model."""
    aliases = []
    for alias, canonical in MODEL_ALIASES.items():
      if canonical == model_id:
        aliases.append(alias)
    return aliases
