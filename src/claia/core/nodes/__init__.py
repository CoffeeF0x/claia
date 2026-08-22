"""
Built-in nodes.

A node is a place compute lives: it hosts deployments, owns instance
lifecycle/reuse, and streams the generate contract back.
"""

from .base import BaseNode
from .local import LocalNode

__all__ = ['BaseNode', 'LocalNode']
