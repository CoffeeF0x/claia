"""
Model name resolution and source selection.

This module handles resolving model names/aliases and selecting the appropriate
source for model loading.
"""

import logging
from typing import List, Optional

# Internal dependencies
from ..plugins import PluginManager
from ..sources import model_sources


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                               CLASSES                                #
########################################################################
class ModelResolver:
  """
  Handles model name resolution and source selection.

  This component is responsible for:
  - Resolving model names and aliases to canonical names
  - Finding available sources for models
  - Selecting the best source based on availability and preferences
  """

  def __init__(self, plugin_manager: PluginManager):
    """Initialize the resolver with a plugin manager."""
    self.plugin_manager = plugin_manager

  def resolve_model_name(self, model_name: str) -> str:
    """
    Resolve a model name or alias to its canonical name.

    Args:
        model_name: Model name or alias to resolve

    Returns:
        Canonical model name if found, original name otherwise
    """
    return self.plugin_manager.resolve_model_name(model_name)

  def find_available_sources(self, model_name: str) -> List[str]:
    """
    Find available sources for a given model name.

    Args:
        model_name: Canonical model name

    Returns:
        List of available source names
    """
    supported_models = self.plugin_manager.get_supported_models()

    if model_name in supported_models:
      model_info = supported_models[model_name]
      available_sources = []

      # Check each source to see if it's available
      for source in model_info.sources.keys():
        if self._is_source_available(source):
          available_sources.append(source)

      logger.debug(f"Found {len(available_sources)} available sources for {model_name}: {available_sources}")
      return available_sources

    logger.debug(f"No sources found for model {model_name}")
    return []

  def select_source(self, model_name: str, available_sources: List[str], active_model_source: Optional[str] = None) -> str:
    """
    Select the appropriate source for the model.

    Args:
        model_name: Name of the model
        available_sources: List of available sources
        active_model_source: Optional source preference

    Returns:
        The selected source name
    """
    if not available_sources:
      raise ValueError(f"No available sources for model {model_name}")

    # If a specific source is requested and available, use it
    if active_model_source and active_model_source in available_sources:
      logger.debug(f"Using requested source {active_model_source} for {model_name}")
      return active_model_source

    # Otherwise, use priority order: transformers > api sources > remote
    source_priority = ["transformers", "openai", "anthropic", "openrouter", "runpod", "vllm"]

    for preferred_source in source_priority:
      if preferred_source in available_sources:
        logger.debug(f"Selected source {preferred_source} for {model_name}")
        return preferred_source

    # Fall back to first available source
    selected_source = available_sources[0]
    logger.debug(f"Using fallback source {selected_source} for {model_name}")
    return selected_source

  def _is_source_available(self, source: str) -> bool:
    """
    Check if a source is available/configured.

    Args:
        source: Source name to check

    Returns:
        True if source is available
    """
    # For now, assume all sources are available
    # In the future, this could check API keys, local installations, etc.
    return source in model_sources
