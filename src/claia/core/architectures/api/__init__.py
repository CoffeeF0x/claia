"""
Hosted-API architecture implementations.

Architectures for provider APIs (OpenAI, Anthropic, OpenRouter), all
served by the ``api`` deployment. ``wire`` holds the SSE/error
utilities they share.
"""

from .openai import OpenAIArchitecture
from .anthropic import AnthropicArchitecture
from .openrouter import OpenRouterArchitecture

__all__ = ['OpenAIArchitecture', 'AnthropicArchitecture', 'OpenRouterArchitecture']
