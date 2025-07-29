"""
Transformers model plugin.

Provides local transformer models via HuggingFace transformers library.
"""

import logging
from typing import Dict, Any, List, Type

# Internal dependencies
from common.results import Result
from ..hooks.model_hooks import ModelInfo
from ..transformers.gemma3 import Gemma3Model


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                              CONSTANTS                               #
########################################################################
# Available transformer models
TRANSFORMER_MODELS = {
  "google/gemma-3-27b-it": {
    "name": "google/gemma-3-27b-it",
    "title": "Gemma 3 27B Instruct",
    "model_type": "transformers",
    "provider": "google",
    "model_class": Gemma3Model
  },
  "google/gemma-3-9b-it": {
    "name": "google/gemma-3-9b-it",
    "title": "Gemma 3 9B Instruct",
    "model_type": "transformers",
    "provider": "google",
    "model_class": Gemma3Model
  },
  "google/gemma-3-2b-it": {
    "name": "google/gemma-3-2b-it",
    "title": "Gemma 3 2B Instruct",
    "model_type": "transformers",
    "provider": "google",
    "model_class": Gemma3Model
  }
}

# Model aliases
MODEL_ALIASES = {
  "gemma": "google/gemma-3-27b-it",
  "gemma-3": "google/gemma-3-27b-it",
  "gemma-27b": "google/gemma-3-27b-it",
  "gemma-9b": "google/gemma-3-9b-it",
  "gemma-2b": "google/gemma-3-2b-it",
  "local": "google/gemma-3-9b-it"
}


########################################################################
#                               CLASSES                                #
########################################################################
class TransformersPlugin:
  """
  Transformers model plugin providing local models via HuggingFace transformers.
  """

  def get_supported_models(self) -> List[ModelInfo]:
    """Get list of supported transformer models."""
    models = []
    for model_id, model_data in TRANSFORMER_MODELS.items():
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
      if model_name not in TRANSFORMER_MODELS:
        return Result.fail(f"Unsupported transformer model: {model_name}")

      model_class = TRANSFORMER_MODELS[model_name]["model_class"]
      return Result(data=model_class)

    except Exception as e:
      logger.error(f"Error getting transformer model class for {model_name}: {str(e)}")
      return Result.fail(f"Failed to get model class: {str(e)}")

  def resolve_model_name(self, model_name: str) -> str:
    """Resolve model name from alias to canonical name."""
    return MODEL_ALIASES.get(model_name, model_name)

  def supports_specialized_loading(self, model_name: str) -> bool:
    """Check if model supports specialized loading."""
    # Transformer models typically need specialized loading
    return True

  def _get_aliases_for_model(self, model_id: str) -> List[str]:
    """Get aliases that point to this model."""
    aliases = []
    for alias, canonical in MODEL_ALIASES.items():
      if canonical == model_id:
        aliases.append(alias)
    return aliases
