"""
Hook specifications for architecture plugins.

Architecture plugins implement specific AI model architectures
(e.g., OpenAI models, Anthropic models, Transformers, etc.)
"""

import pluggy
from typing import Optional, Dict, List, Any, Type
from dataclasses import dataclass

# Internal dependencies
from common.results import Result
from common.enums.model import ModelCapability


@dataclass
class ArchitectureInfo:
  """Information about an architecture provided by an architecture plugin."""
  name: str
  title: str
  description: str
  supported_models: List[str]
  capabilities: List[ModelCapability]


# Create hookspec decorator
hookspec = pluggy.HookspecMarker("claia_architectures")


class ArchitectureHooks:
  """Hook specifications for architecture plugins."""

  @hookspec
  def get_architecture_info(self) -> ArchitectureInfo:
    """
    Get information about this architecture.

    Returns:
        ArchitectureInfo object describing this architecture
    """

  @hookspec
  def get_supported_models(self) -> Dict[str, Any]:
    """
    Get all models supported by this architecture plugin.

    Returns:
        Dict mapping model names to model information
    """

  @hookspec
  def get_model_class(self, model_name: str) -> Optional[Type]:
    """
    Get the model class for a specific model.

    Args:
        model_name: Canonical model name

    Returns:
        Model class if supported, None otherwise
    """

  @hookspec
  def get_model_id(self, model_name: str) -> Optional[str]:
    """
    Get the actual model ID/path for a model.

    Args:
        model_name: Canonical model name

    Returns:
        Model ID/path if available, None otherwise
    """

  @hookspec
  def supports_specialized_loading(self, model_name: str) -> bool:
    """
    Check if this architecture supports specialized loading for the model.

    Args:
        model_name: Canonical model name

    Returns:
        True if specialized loading is supported
    """
