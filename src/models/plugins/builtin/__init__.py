"""
Built-in plugins for the CLAIA models system.

This package contains the default plugins that provide support for
the core model types and providers.
"""

from .api_plugin import APIPlugin
from .transformers_plugin import TransformersPlugin
from .specialized_plugin import SpecializedPlugin

__all__ = ['APIPlugin', 'TransformersPlugin', 'SpecializedPlugin']
