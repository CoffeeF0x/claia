"""
Base architecture classes for the CLAIA serving stack.

This module provides the foundational classes that all architecture
implementations inherit from.
"""

from .base import BaseArchitecture
from .api import APIArchitecture
from .local import LocalArchitecture

__all__ = ['BaseArchitecture', 'APIArchitecture', 'LocalArchitecture']
