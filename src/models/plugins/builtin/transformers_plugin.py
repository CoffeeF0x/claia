"""
Transformers models plugin.

This plugin provides support for local transformers-based models.
"""

from typing import Optional, Dict, Type
import logging

# Internal dependencies
from common.enums.model import ModelCapability
from common.results import Result
from ...base import BaseModel
from ...transformers import TransformersModel, DiffusionModel
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
class TransformersPlugin(ModelPlugin):
  """Plugin for transformers-based local models."""

  def __init__(self):
    super().__init__()

    # Define supported models
    self._supported_models = {
      "llama-3.1-8b-instruct": ModelInfo(
        name="llama-3.1-8b-instruct",
        title="Llama 3.1 8B Instruct",
        description="Meta's Llama 3.1 8B parameter instruction-tuned model.",
        capabilities=[ModelCapability.TTT],
        sources={
          "transformers": ["meta-llama/Meta-Llama-3.1-8B-Instruct"]
        },
        aliases=["llama3.1-8b", "llama-8b"]
      ),
      "stable-diffusion-xl": ModelInfo(
        name="stable-diffusion-xl",
        title="Stable Diffusion XL",
        description="High-resolution text-to-image diffusion model.",
        capabilities=[ModelCapability.TTI],
        sources={
          "transformers": ["stabilityai/stable-diffusion-xl-base-1.0"]
        },
        aliases=["sdxl", "stable-diffusion"]
      ),
      "qwen2.5-7b-instruct": ModelInfo(
        name="qwen2.5-7b-instruct",
        title="Qwen2.5 7B Instruct",
        description="Alibaba's Qwen2.5 7B parameter instruction-tuned model.",
        capabilities=[ModelCapability.TTT],
        sources={
          "transformers": ["Qwen/Qwen2.5-7B-Instruct"]
        },
        aliases=["qwen2.5-7b", "qwen-7b"]
      )
    }

    # Map capabilities to model classes
    self._capability_classes = {
      ModelCapability.TTT: TransformersModel,
      ModelCapability.TTI: DiffusionModel
    }

  def get_model_class(self, model_name: str, source: str, capability: Optional[ModelCapability] = None) -> Optional[Type[BaseModel]]:
    """Get the model class for transformers models."""
    # Only handle transformers source
    if source != "transformers":
      return None

    # Check if we support this model
    if model_name in self._supported_models:
      model_info = self._supported_models[model_name]

      # Determine the appropriate class based on capabilities
      primary_capability = model_info.capabilities[0] if model_info.capabilities else ModelCapability.TTT
      if capability and capability in model_info.capabilities:
        primary_capability = capability

      if primary_capability in self._capability_classes:
        model_class = self._capability_classes[primary_capability]
        logger.debug(f"TransformersPlugin providing {model_class.__name__} for {model_name}")
        return model_class

    return None

  def get_supported_models(self) -> Dict[str, ModelInfo]:
    """Get all models supported by this plugin."""
    return self._supported_models.copy()

  def create_model(self, model_name: str, source: str, config: ModelConfig, capability: Optional[ModelCapability] = None, device: Optional[str] = None) -> Result:
    """Create a transformers model instance."""
    try:
      # Only handle transformers source
      if source != "transformers":
        return Result.fail(f"TransformersPlugin does not support source: {source}")
      
      # Get model class and ID
      model_class = self.get_model_class(model_name, source, capability)
      if not model_class:
        return Result.fail(f"No model class found for {model_name}/{source}")
      
      model_id = self.get_model_id(model_name, source)
      if not model_id:
        return Result.fail(f"No model ID found for {model_name}/{source}")
      
      logger.debug(f"Creating {model_class.__name__} for {model_name} (ID: {model_id})")
      
      # Create model instance
      model = model_class(
        model_name=model_id,
        models_directory=config.models_directory,
        device=device
      )
      
      return Result.success(model)
      
    except Exception as e:
      logger.error(f"Error creating transformers model {model_name}: {str(e)}")
      return Result.fail(f"Failed to create transformers model: {str(e)}")

  def get_model_id(self, model_name: str, source: str) -> Optional[str]:
    """Get the model ID for transformers models."""
    if source == "transformers" and model_name in self._supported_models:
      model_info = self._supported_models[model_name]
      if "transformers" in model_info.sources:
        return model_info.sources["transformers"][0]

    return None
