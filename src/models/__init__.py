"""
Models package for CLAIA.
Imports model classes and the ModelRegistry from their respective modules.
"""

from .base import APIModel, LocalModel
from .api import OpenAIModel, AnthropicModel, RunpodModel, OpenRouterModel
from .transformers import TransformersModel, Gemma3Model, DiffusionModel
from .remote import VLLMModel
from .registry import ModelRegistry
from .definitions import model_definitions, DEFAULT_SETTINGS
from .sources import model_sources
