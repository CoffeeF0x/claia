"""
Built-in deployments.

A deployment serves an architecture on a node: it deploys the
requested architecture and relays + meters the generate stream.
"""

from .base import BaseDeployment
from .dummy import DummyDeployment
from .api import APIDeployment
from .transformers import TransformersDeployment

__all__ = [
  'BaseDeployment',
  'DummyDeployment',
  'APIDeployment',
  'TransformersDeployment',
]
