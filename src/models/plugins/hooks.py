"""
Hook specifications for the model plugin system.

This module defines the interfaces that plugins must implement to integrate
with the CLAIA model system.
"""

import pluggy
from typing import Optional, Dict, List, Any, Type
from dataclasses import dataclass

# Internal dependencies
from ..base import BaseModel
from common.enums.model import ModelCapability


@dataclass
class ModelInfo:
  """Information about a model provided by a plugin."""
  name: str
  title: str
  description: str
  capabilities: List[ModelCapability]
  sources: Dict[str, List[str]]  # source -> model_ids
  aliases: Optional[List[str]] = None
  settings: Optional[Dict[str, Any]] = None


# Create hookspec decorator
hookspec = pluggy.HookspecMarker("claia_models")


class ModelHooks:
  """Hook specifications for model plugins."""

  @hookspec
  def get_model_class(self, model_name: str, source: str, capability: Optional[ModelCapability] = None) -> Optional[Type[BaseModel]]:
    """
    Get the model class for a specific model and source.

    Args:
        model_name: Canonical model name
        source: Source/provider (e.g., 'openai', 'transformers')
        capability: Optional specific capability needed

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
  def get_model_id(self, model_name: str, source: str) -> Optional[str]:
    """
    Get the actual model ID/path for a model and source.

    Args:
        model_name: Canonical model name
        source: Source/provider

    Returns:
        Model ID/path if supported, None otherwise
    """

  @hookspec
  def supports_specialized_loading(self, model_name: str) -> bool:
    """
    Check if this plugin provides specialized loading for a model.

    Args:
        model_name: Model name to check

    Returns:
        True if this plugin handles specialized loading
    """
