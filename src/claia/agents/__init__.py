"""
Agent module for the claia project.
Contains AI agents which define specific processes for managing the conversation flow.

Features a plugin-based architecture for extensibility:
- AgentRegistry: Plugin-based registry for agent management
- Plugin system for adding custom agents without modifying core code
"""

# Internal dependencies
from .lib import Process, ProcessQueue, BaseAgent
from .registry import AgentRegistry


__all__ = [
    'Process',              # Process class for work units
    'ProcessQueue',         # Queue for managing processes
    'BaseAgent',            # Base class for agent implementations
    'AgentRegistry',        # Plugin-based registry
]
