"""
Internal architecture plugins.

This package contains built-in architecture plugins for different
types of AI models and providers.
"""

# Import architecture plugins
from .openai import OpenAIPlugin
from .anthropic import AnthropicPlugin
from .transformers_generic import TransformersGenericPlugin
from .transformers_gemma3 import TransformersGemma3Plugin
from .dummy import DummyArchitecturePlugin

# Export all plugins
__all__ = [
  'OpenAIPlugin',
  'AnthropicPlugin',
  'TransformersGenericPlugin',
  'TransformersGemma3Plugin',
  'DummyArchitecturePlugin'
]
