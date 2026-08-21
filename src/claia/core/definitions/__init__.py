"""
Model definition providers.

This package provides comprehensive model definitions organized by provider/type.
"""

from .legacy import LegacyDefinitions
from .openai import OpenAIDefinitions
from .anthropic import AnthropicDefinitions
from .openrouter import OpenRouterDefinitions

__all__ = [
  "LegacyDefinitions",
  "OpenAIDefinitions",
  "AnthropicDefinitions",
  "OpenRouterDefinitions"
]
