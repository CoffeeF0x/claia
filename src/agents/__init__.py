"""
Agent module for the claia project.
Contains AI agents which define specific processes for managing the conversation flow.

Features a plugin-based architecture for extensibility:
- AgentRegistry: Plugin-based registry for agent management
- Plugin system for adding custom agents without modifying core code
"""

# External dependencies
import logging

# Internal dependencies
from .lib import Process, ProcessQueue, Agent, BaseAgent
from .registry import AgentRegistry
from .manager import AgentManager


__all__ = [
    'Process',              # Process class for work units
    'ProcessQueue',         # Queue for managing processes
    'Agent',                # Main agent dispatcher
    'BaseAgent',            # Base class for agent implementations
    'AgentRegistry',        # Plugin-based registry
    'AgentManager'          # Plugin management
]
