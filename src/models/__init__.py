"""
Models module for the claia project.
Contains model definitions, deployment methods, and inference engine.

Features a plugin-based architecture for extensibility:
- ModelRegistry: Refactored with plugin system for extensibility
- Plugin system for adding custom models without modifying core code
"""

# Main registry with plugin-based architecture
from .registry import ModelRegistry
from .config import ModelConfig

# Plugin system components for external developers
from .plugins import PluginManager, ModelPlugin

__all__ = [
    'ModelRegistry',        # Plugin-based registry
    'ModelConfig',
    'PluginManager',        # Plugin management
    'ModelPlugin'           # Base class for custom plugins
]
