"""
Specialized models plugin.

This plugin provides support for models that require specialized implementations,
like Gemma3, that can't use the standard TransformersModel class.
"""

from typing import Optional, Dict, Type
import logging

# Internal dependencies
from common.enums.model import ModelCapability
from common.results import Result
from ...base import BaseModel
from ...transformers import Gemma3Model
from ...config import ModelConfig
from ..base import ModelPlugin
from ..hooks import ModelInfo


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                               CLASSES                                #
########################################################################
class SpecializedPlugin(ModelPlugin):
  """Plugin for models requiring specialized implementations."""

  def __init__(self):
    super().__init__()

    # Define specialized models
    self._specialized_models = {
      "gemma-3-2b-it": ModelInfo(
        name="gemma-3-2b-it",
        title="Gemma 3 2B Instruct",
        description="Google's Gemma 3 2B parameter instruction-tuned model.",
        capabilities=[ModelCapability.TTT],
        sources={
          "transformers": ["google/gemma-3-2b-it"]
        },
        aliases=["gemma3-2b", "gemma-2b"]
      ),
      "gemma-3-9b-it": ModelInfo(
        name="gemma-3-9b-it",
        title="Gemma 3 9B Instruct",
        description="Google's Gemma 3 9B parameter instruction-tuned model.",
        capabilities=[ModelCapability.TTT],
        sources={
          "transformers": ["google/gemma-3-9b-it"]
        },
        aliases=["gemma3-9b", "gemma-9b"]
      ),
      "gemma-3-27b-it": ModelInfo(
        name="gemma-3-27b-it",
        title="Gemma 3 27B Instruct",
        description="Google's Gemma 3 27B parameter instruction-tuned model.",
        capabilities=[ModelCapability.TTT, ModelCapability.TAI],
        sources={
          "transformers": ["google/gemma-3-27b-it"]
        },
        aliases=["gemma3-27b", "gemma-27b"]
      )
    }

  def get_model_class(self, model_name: str, source: str, capability: Optional[ModelCapability] = None) -> Optional[Type[BaseModel]]:
    """Get the model class for specialized models."""
    # Only handle transformers source for specialized models
    if source != "transformers":
      return None

    # Check if this is a specialized model we handle
    if model_name in self._specialized_models:
      logger.debug(f"SpecializedPlugin providing Gemma3Model for {model_name}")
      return Gemma3Model

    return None

  def get_supported_models(self) -> Dict[str, ModelInfo]:
    """Get all specialized models supported by this plugin."""
    return self._specialized_models.copy()

  def get_model_id(self, model_name: str, source: str) -> Optional[str]:
    """Get the model ID for specialized models."""
    if source == "transformers" and model_name in self._specialized_models:
      model_info = self._specialized_models[model_name]
      if "transformers" in model_info.sources:
        return model_info.sources["transformers"][0]

    return None

  def create_model(self, model_name: str, source: str, config: ModelConfig, capability: Optional[ModelCapability] = None, device: Optional[str] = None) -> Result:
    """Create a specialized model instance."""
    try:
      # Only handle transformers source
      if source != "transformers":
        return Result.fail(f"SpecializedPlugin does not support source: {source}")
      
      # Get model class and ID
      model_class = self.get_model_class(model_name, source, capability)
      if not model_class:
        return Result.fail(f"No specialized model class found for {model_name}/{source}")
      
      model_id = self.get_model_id(model_name, source)
      if not model_id:
        return Result.fail(f"No model ID found for {model_name}/{source}")
      
      logger.debug(f"Creating {model_class.__name__} for {model_name} (ID: {model_id})")
      
      # Create specialized model instance
      model = model_class(
        model_name=model_id,
        models_directory=config.models_directory,
        device=device
      )
      
      return Result.success(model)
      
    except Exception as e:
      logger.error(f"Error creating specialized model {model_name}: {str(e)}")
      return Result.fail(f"Failed to create specialized model: {str(e)}")

  def supports_specialized_loading(self, model_name: str) -> bool:
    """Check if this plugin provides specialized loading."""
    return model_name in self._specialized_models
