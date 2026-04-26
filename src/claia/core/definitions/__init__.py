"""
Model definitions plugin package.

This package provides comprehensive model definitions organized by provider/type.
"""

# Import model definitions plugins
from .legacy import LegacyDefinitionsPlugin
from .openai import OpenAIDefinitionsPlugin
from .anthropic import AnthropicDefinitionsPlugin
from .openrouter import OpenRouterDefinitionsPlugin

# Export all plugins
__all__ = [
  "LegacyDefinitionsPlugin",
  "OpenAIDefinitionsPlugin",
  "AnthropicDefinitionsPlugin",
  "OpenRouterDefinitionsPlugin"
]
