"""
CLAIA Unified Library

This library provides foundational classes for the CLAIA system:
- Agent base classes and utilities
- Process management
- Queue management
- Results handling
- Model architecture components (under model/ subdirectory)
- File handling utilities
- Enums and type definitions

Usage:
    from claia.lib import BaseAgent, Process, ProcessQueue
    from claia.lib.model import BaseModel, APIModel, LocalModel
"""

# Core agent and process classes
from .base import BaseAgent
from .process import Process
from .queue import ProcessQueue
from .results import Result

# Model classes are under model/ subdirectory
from .model import BaseModel, APIModel, LocalModel

__all__ = [
  # Core classes
  'BaseAgent', 'Process', 'ProcessQueue', 'Result',

  # Model base classes (re-exported for convenience)
  'BaseModel', 'APIModel', 'LocalModel'
]
