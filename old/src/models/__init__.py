"""
Models package for CLAIA.
Imports model classes and the ModelRegistry from their respective modules.
"""

from .definitions import model_definitions, DEFAULT_SETTINGS
from .sources import model_sources
from .registry import ModelRegistry
from .base import APIModel, LocalModel
from .api import OpenAIModel, AnthropicModel, RunpodModel, OpenRouterModel
from .transformers import TransformersModel, Gemma3Model, DiffusionModel
from .remote import VLLMModel
from .dummy import DummyModel
