"""
Internal architecture plugins.

This package contains built-in architecture plugins for different
types of AI models and providers.
"""

# Import architecture plugins
from .openai import OpenAIPlugin
from .anthropic import AnthropicPlugin
from .transformers import TransformersPlugin
from .dummy import DummyArchitecturePlugin

# Export all plugins
__all__ = [
  'OpenAIPlugin',
  'AnthropicPlugin',
  'TransformersPlugin',
  'DummyArchitecturePlugin'
]
