"""
API models plugin.

This plugin provides support for API-based models like OpenAI, Anthropic, etc.
"""

from typing import Optional, Dict, Type
import logging

# Internal dependencies
from common.enums.model import ModelCapability
from common.results import Result
from ...base import BaseModel
from ...api import OpenAIModel, AnthropicModel, RunpodModel, OpenRouterModel
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
class APIPlugin(ModelPlugin):
  """Plugin for API-based model providers."""

  def __init__(self):
    super().__init__()

    # Define supported models
    self._supported_models = {
      "gpt-4": ModelInfo(
        name="gpt-4",
        title="GPT 4",
        description="Snapshot of gpt-4 from June 13th 2023 with improved function calling support.",
        capabilities=[ModelCapability.TTT],
        sources={
          "openai": ["gpt-4-0613", "gpt-4"],
          "openrouter": ["openai/gpt-4"]
        },
        aliases=["gpt4", "gpt-4-0613"]
      ),
      "claude-3-5-sonnet": ModelInfo(
        name="claude-3-5-sonnet",
        title="Claude 3.5 Sonnet",
        description="Claude 3.5 Sonnet sets new industry benchmarks for graduate-level reasoning.",
        capabilities=[ModelCapability.TTT],
        sources={
          "anthropic": ["claude-3-5-sonnet-20241022"],
          "openrouter": ["anthropic/claude-3.5-sonnet"]
        },
        aliases=["claude-3.5-sonnet", "sonnet"]
      ),
      "gpt-4o": ModelInfo(
        name="gpt-4o",
        title="GPT-4o",
        description="GPT-4 Omni multimodal model with vision capabilities.",
        capabilities=[ModelCapability.TTT, ModelCapability.TAI],
        sources={
          "openai": ["gpt-4o"],
          "openrouter": ["openai/gpt-4o"]
        },
        aliases=["gpt4o"]
      )
    }

    # Map sources to model classes
    self._source_classes = {
      "openai": OpenAIModel,
      "anthropic": AnthropicModel,
      "runpod": RunpodModel,
      "openrouter": OpenRouterModel
    }

  def get_model_class(self, model_name: str, source: str, capability: Optional[ModelCapability] = None) -> Optional[Type[BaseModel]]:
    """Get the model class for API models."""
    # Check if we support this model and source
    if model_name in self._supported_models:
      model_info = self._supported_models[model_name]
      if source in model_info.sources and source in self._source_classes:
        logger.debug(f"APIPlugin providing {self._source_classes[source].__name__} for {model_name}/{source}")
        return self._source_classes[source]

    return None

  def get_supported_models(self) -> Dict[str, ModelInfo]:
    """Get all models supported by this plugin."""
    return self._supported_models.copy()

  def create_model(self, model_name: str, source: str, config: ModelConfig, capability: Optional[ModelCapability] = None, device: Optional[str] = None) -> Result:
    """Create an API model instance."""
    try:
      # Get model class and ID
      model_class = self.get_model_class(model_name, source, capability)
      if not model_class:
        return Result.fail(f"No model class found for {model_name}/{source}")
      
      model_id = self.get_model_id(model_name, source)
      if not model_id:
        return Result.fail(f"No model ID found for {model_name}/{source}")
      
      # Get API key for this source
      api_key = config.get_api_token(source)
      if not api_key:
        return Result.fail(f"No API key configured for source: {source}")
      
      logger.debug(f"Creating {model_class.__name__} for {model_name} (ID: {model_id})")
      
      # Create model instance
      model = model_class(
        model_name=model_id,
        api_key=api_key
      )
      
      return Result.success(model)
      
    except Exception as e:
      logger.error(f"Error creating API model {model_name}: {str(e)}")
      return Result.fail(f"Failed to create API model: {str(e)}")

  def get_model_id(self, model_name: str, source: str) -> Optional[str]:
    """Get the model ID for API models."""
    if model_name in self._supported_models:
      model_info = self._supported_models[model_name]
      if source in model_info.sources:
        # Return the first model ID for the source
        return model_info.sources[source][0]

    return None
