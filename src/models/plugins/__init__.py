"""
Plugin system for the CLAIA models package.

This module provides the plugin architecture that allows dynamic registration
and discovery of model implementations.
"""

from .hooks import ModelHooks
from .manager import PluginManager
from .base import ModelPlugin

__all__ = ['ModelHooks', 'PluginManager', 'ModelPlugin']
