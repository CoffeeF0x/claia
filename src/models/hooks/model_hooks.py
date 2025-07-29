"""
Hook specifications for model plugins.

Model plugins are responsible for implementing specific AI models
(e.g., OpenAI GPT, Transformers models, etc.)
"""

import pluggy
from typing import Optional, Dict, List, Any, Type
from dataclasses import dataclass

# Internal dependencies
from ..base import BaseModel
from common.enums.model import ModelCapability


@dataclass
class ModelInfo:
  """Information about a model provided by a model plugin."""
  name: str
  title: str
  description: str
  capabilities: List[ModelCapability]
  aliases: Optional[List[str]] = None
  settings: Optional[Dict[str, Any]] = None


# Create hookspec decorator
hookspec = pluggy.HookspecMarker("claia_models")


class ModelHooks:
  """Hook specifications for model plugins."""

  @hookspec
  def get_model_class(self, model_name: str) -> Optional[Type[BaseModel]]:
    """
    Get the model class for a specific model.

    Args:
        model_name: Canonical model name

    Returns:
        Model class if this plugin handles it, None otherwise
    """

  @hookspec
  def get_supported_models(self) -> Dict[str, ModelInfo]:
    """
    Get all models supported by this plugin.

    Returns:
        Dict mapping model names to ModelInfo objects
    """

  @hookspec
  def get_model_id(self, model_name: str) -> Optional[str]:
    """
    Get the actual model ID/path for a model.

    Args:
        model_name: Canonical model name

    Returns:
        Model ID/path if supported, None otherwise
    """
