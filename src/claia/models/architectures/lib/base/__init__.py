"""
Base model classes for the CLAIA architecture system.

This module provides the foundational classes that all model implementations inherit from.
"""

from .base import BaseModel
from .api import APIModel
from .local import LocalModel

__all__ = ['BaseModel', 'APIModel', 'LocalModel']
