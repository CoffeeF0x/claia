"""
CLAIA AI Assistant Framework

A flexible framework for building AI assistants with pluggable architectures,
deployments, and agents.
"""

__version__ = "0.1.0"

# Import main modules to make them available at package level
try:
  from . import cli
  # from . import commands
  from . import agents
  from . import models
  from . import common
except ImportError:
  # Allow graceful degradation during development
  pass

__all__ = ["cli", "agents", "models", "common"]
