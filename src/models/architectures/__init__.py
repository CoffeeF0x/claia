"""
Internal model plugins.

This package contains built-in model plugins for different
types of AI models and providers.
"""

# Import model plugins
from .openai_plugin import OpenAIPlugin
from .anthropic_plugin import AnthropicPlugin
from .transformers_plugin import TransformersPlugin

# Export all plugins
__all__ = [
  'OpenAIPlugin',
  'AnthropicPlugin',
  'TransformersPlugin'
]
