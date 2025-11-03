"""
Base model abstract class.

This module defines the foundational BaseModel class that all model implementations inherit from.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any

# Internal dependencies
from claia.lib.data import Conversation


########################################################################
#                              CONSTANTS                               #
########################################################################
# Common model defaults
DEFAULT_SETTINGS = {
  "max_tokens": 1000,
  "temperature": 0.7,
  "top_p": 1.0,
  "top_k": None,
  "n": 1,
  "stop": None,
  "stream": True
}


########################################################################
#                               CLASSES                                #
########################################################################
class BaseModel(ABC):
  """Abstract base class for all model implementations."""

  def __init__(self, model_name: str):
    self.model_name = model_name
    self.default_settings = DEFAULT_SETTINGS.copy()

  @abstractmethod
  def generate(self, conversation: Conversation, **kwargs) -> str:
    """Generate a response based on the given conversation."""
    pass

  def update_settings(self, model_settings: Dict[str, Any], conversation: Conversation, **kwargs) -> Dict[str, Any]:
    """
    Extract settings from the conversation object, falling back to defaults.

    Args:
        model_settings: Model-specific settings to override default settings
        conversation: The conversation containing settings
        **kwargs: Additional keyword arguments to override settings

    Returns:
        Dict[str, Any]: The settings dictionary with defaults applied where needed
    """
    # Start with our base defaults
    settings = self.default_settings.copy()

    # Apply model-specific settings
    if model_settings:
      settings.update(model_settings)

    # Get conversation settings if available
    conversation_settings = conversation.get_settings()
    if conversation_settings:
      # Override with streaming setting
      settings["stream"] = conversation_settings.streaming

      # Override with text settings if available
      text_settings = conversation_settings.text_settings
      if text_settings:
        if "max_tokens" in text_settings and text_settings["max_tokens"] is not None:
          settings["max_tokens"] = text_settings["max_tokens"]

        if "temperature" in text_settings and text_settings["temperature"] is not None:
          settings["temperature"] = text_settings["temperature"]

        if "top_p" in text_settings and text_settings["top_p"] is not None:
          settings["top_p"] = text_settings["top_p"]

        if "top_k" in text_settings and text_settings["top_k"] is not None:
          settings["top_k"] = text_settings["top_k"]

        if "presence_penalty" in text_settings and text_settings["presence_penalty"] is not None:
          settings["presence_penalty"] = text_settings["presence_penalty"]

        if "frequency_penalty" in text_settings and text_settings["frequency_penalty"] is not None:
          settings["frequency_penalty"] = text_settings["frequency_penalty"]

    # Apply any additional overrides from kwargs
    settings.update({k: v for k, v in kwargs.items() if k in settings})

    return settings
