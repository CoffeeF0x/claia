"""
Base plugin class for model implementations.

This module provides the base class that all model plugins should inherit from.
"""

from abc import ABC
from typing import Optional, Dict, Type, List
from dataclasses import dataclass

# Internal dependencies
from common.enums.model import ModelCapability
from common.results import Result
from ..base import BaseModel
from ..config import ModelConfig
from .hooks import ModelInfo, ModelHooks


class ModelPlugin(ABC):
  """
  Base class for model plugins.

  Plugins should inherit from this class and implement the required methods
  to provide model implementations for the CLAIA system.
  """

  def __init__(self):
    """Initialize the plugin."""
    self.plugin_name = self.__class__.__name__

  def get_model_class(self, model_name: str, source: str, capability: Optional[ModelCapability] = None) -> Optional[Type[BaseModel]]:
    """
    Get the model class for a specific model and source.

    Override this method to provide model classes for specific models.

    Args:
        model_name: Canonical model name
        source: Source/provider (e.g., 'openai', 'transformers')
        capability: Optional specific capability needed

    Returns:
        Model class if this plugin handles it, None otherwise
    """
    return None

  def get_supported_models(self) -> Dict[str, ModelInfo]:
    """
    Get all models supported by this plugin.

    Override this method to declare which models this plugin supports.

    Returns:
        Dict mapping model names to ModelInfo objects
    """
    return {}

  def get_model_id(self, model_name: str, source: str) -> Optional[str]:
    """
    Get the actual model ID/path for a model and source.

    Override this method to provide source-specific model IDs.

    Args:
        model_name: Canonical model name
        source: Source/provider

    Returns:
        Model ID/path if supported, None otherwise
    """
    return None

  def create_model(self, model_name: str, source: str, config: ModelConfig, capability: Optional[ModelCapability] = None, device: Optional[str] = None) -> Result:
    """
    Create a model instance.

    Override this method to provide model creation logic.

    Args:
        model_name: Name of the model to create
        source: Selected source for the model
        config: ModelConfig containing API keys and settings
        capability: Optional capability filter
        device: Optional device specification

    Returns:
        Result containing the model instance or error
    """
    return Result.fail(f"Plugin {self.plugin_name} does not implement create_model")

  def supports_specialized_loading(self, model_name: str) -> bool:
    """
    Check if this plugin provides specialized loading for a model.

    Override this method if your plugin provides custom loading logic.

    Args:
        model_name: Model name to check

    Returns:
        True if this plugin handles specialized loading
    """
    return False
