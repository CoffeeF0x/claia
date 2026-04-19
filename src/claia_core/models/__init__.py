"""
Model architecture components for CLAIA.

This module contains all the base classes and utilities for model architectures:
- base: Base model classes
- api: API-based model implementations
- transformers: Transformer-based model implementations
- dummy: Dummy models for testing
"""

# Re-export main model base classes for convenience
from .base import BaseModel, APIModel, LocalModel
from .api import AnthropicModel, OpenAIModel
from .transformers import GenericTransformerModel, Gemma3Model
from .dummy import DummyModel

__all__ = [
  'BaseModel', 'APIModel', 'LocalModel',
  'AnthropicModel', 'OpenAIModel',
  'GenericTransformerModel', 'Gemma3Model',
  'DummyModel'
]
