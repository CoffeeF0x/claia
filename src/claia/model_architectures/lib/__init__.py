"""
CLAIA Model Architecture Library

This library provides the foundational classes and implementations for all model
architectures in the CLAIA system. It is organized into three main categories:

- base: Abstract base classes for all model types
- api: API-based model implementations (OpenAI, Anthropic, etc.)
- transformers: Local transformer model implementations

The library follows a clean separation of concerns:
- Base classes define common interfaces and functionality
- API models handle cloud-based AI services
- Transformer models handle local deployment of transformer architectures

Usage:
    from claia.model_architectures.lib.base import BaseModel, APIModel, LocalModel
    from models.architectures.lib.api import OpenAIModel, AnthropicModel
    from models.architectures.lib.transformers import GenericTransformerModel, Gemma3Model
"""

# Base classes
from .base import BaseModel, APIModel, LocalModel

# API implementations
from .api import OpenAIModel, AnthropicModel

# Transformer implementations
from .transformers import GenericTransformerModel, Gemma3Model

# Dummy implementations
from .dummy import DummyModel

__all__ = [
  # Base classes
  'BaseModel', 'APIModel', 'LocalModel',

  # API models
  'OpenAIModel', 'AnthropicModel',

  # Transformer models
  'GenericTransformerModel', 'Gemma3Model',

  # Dummy models
  'DummyModel'
]
