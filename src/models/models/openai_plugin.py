"""
OpenAI model plugin.

Provides OpenAI API-based models like GPT-4, GPT-3.5-turbo, etc.
"""

import logging
from typing import Dict, Any, List, Type

# Internal dependencies
from common.results import Result
from ..hooks.model_hooks import ModelInfo
from ..api.openai import OpenAIModel


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                              CONSTANTS                               #
########################################################################
# Available OpenAI models
OPENAI_MODELS = {
  "gpt-4": {
    "name": "gpt-4",
    "title": "GPT-4",
    "model_type": "api",
    "provider": "openai"
  },
  "gpt-4-turbo": {
    "name": "gpt-4-turbo",
    "title": "GPT-4 Turbo",
    "model_type": "api",
    "provider": "openai"
  },
  "gpt-4-turbo-preview": {
    "name": "gpt-4-turbo-preview",
    "title": "GPT-4 Turbo Preview",
    "model_type": "api",
    "provider": "openai"
  },
  "gpt-3.5-turbo": {
    "name": "gpt-3.5-turbo",
    "title": "GPT-3.5 Turbo",
    "model_type": "api",
    "provider": "openai"
  },
  "gpt-3.5-turbo-16k": {
    "name": "gpt-3.5-turbo-16k",
    "title": "GPT-3.5 Turbo 16K",
    "model_type": "api",
    "provider": "openai"
  }
}

# Model aliases
MODEL_ALIASES = {
  "openai": "gpt-4",
  "gpt4": "gpt-4",
  "gpt35": "gpt-3.5-turbo",
  "turbo": "gpt-3.5-turbo"
}


########################################################################
#                               CLASSES                                #
########################################################################
class OpenAIPlugin:
  """
  OpenAI model plugin providing GPT models via OpenAI API.
  """

  def get_supported_models(self) -> List[ModelInfo]:
    """Get list of supported OpenAI models."""
    models = []
    for model_id, model_data in OPENAI_MODELS.items():
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
      if model_name not in OPENAI_MODELS:
        return Result.fail(f"Unsupported OpenAI model: {model_name}")

      return Result(data=OpenAIModel)

    except Exception as e:
      logger.error(f"Error getting OpenAI model class for {model_name}: {str(e)}")
      return Result.fail(f"Failed to get model class: {str(e)}")

  def resolve_model_name(self, model_name: str) -> str:
    """Resolve model name from alias to canonical name."""
    return MODEL_ALIASES.get(model_name, model_name)

  def supports_specialized_loading(self, model_name: str) -> bool:
    """Check if model supports specialized loading."""
    # OpenAI models don't need specialized loading
    return False

  def _get_aliases_for_model(self, model_id: str) -> List[str]:
    """Get aliases that point to this model."""
    aliases = []
    for alias, canonical in MODEL_ALIASES.items():
      if canonical == model_id:
        aliases.append(alias)
    return aliases
