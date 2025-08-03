"""
Models module for the claia project.
Contains model definitions, deployment methods, and inference engine.

Features a plugin-based architecture for extensibility:
- ModelRegistry: Refactored with plugin system for extensibility
- Plugin system for adding custom models without modifying core code
"""

# Main registry with plugin-based architecture
from .registry import ModelRegistry
from .manager import ModuleManager

__all__ = [
    'ModelRegistry',        # Plugin-based registry
    'ModuleManager'         # Module manager for plugin system
]
