"""
Core library for the CLAIA agents package.
Contains base classes, process management, and queue functionality.
"""

# Core classes
from .base import BaseAgent
from .process import Process
from .queue import ProcessQueue

# Main agent dispatcher
from .agent import Agent

__all__ = [
  'BaseAgent',
  'Process',
  'ProcessQueue',
  'Agent'
]
