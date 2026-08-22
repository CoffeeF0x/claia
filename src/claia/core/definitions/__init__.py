"""
Model definition providers.

This package provides model definitions organized by company.
"""

from .anthropic import AnthropicDefinitions
from .deepseek import DeepSeekDefinitions
from .legacy import LegacyDefinitions
from .meta import MetaDefinitions
from .minimax import MiniMaxDefinitions
from .moonshot import MoonshotDefinitions
from .openai import OpenAIDefinitions
from .qwen import QwenDefinitions
from .zai import ZaiDefinitions

__all__ = [
  "AnthropicDefinitions",
  "DeepSeekDefinitions",
  "LegacyDefinitions",
  "MetaDefinitions",
  "MiniMaxDefinitions",
  "MoonshotDefinitions",
  "OpenAIDefinitions",
  "QwenDefinitions",
  "ZaiDefinitions",
]
