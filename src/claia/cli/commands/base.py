"""
Base command class for CLAIA CLI commands.

This module provides the base class that all command classes should inherit from.
"""

import logging
from typing import List, Optional, Any
from abc import ABC, abstractmethod

from claia.lib.results import Result
from claia.registry import Registry


logger = logging.getLogger(__name__)


class BaseCommand(ABC):
  """
  Base class for all CLAIA CLI commands.
  
  All command classes should inherit from this class and implement
  the execute method.
  """
  
  def __init__(self, registry: Registry, settings: Any, current_mode: str = 'interactive'):
    """
    Initialize the base command.
    
    Args:
        registry: The unified registry for tools, models, and agents
        settings: The settings object containing configuration
        current_mode: Current execution mode ('interactive' or 'cli')
    """
    self.registry = registry
    self.settings = settings
    self._current_mode = current_mode
    self.logger = logging.getLogger(self.__class__.__name__)
  
  @abstractmethod
  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """
    Execute the command with the given arguments.
    
    Args:
        args: List of command arguments
        conversation: Optional conversation context
    
    Returns:
        Result object indicating success/failure and any output
    """
    pass
  
  def get_help_prefix(self) -> str:
    """
    Get the appropriate command prefix for help messages based on current mode.
    
    Returns:
        Command prefix (e.g., ':' for interactive, '--' for CLI)
    """
    if self._current_mode == 'interactive':
      return ':'
    return '--'
  
  def format_command(self, cmd: str) -> str:
    """
    Format a command string with the appropriate prefix for the current mode.
    
    Args:
        cmd: Command name (without prefix)
    
    Returns:
        Formatted command string
    """
    if self._current_mode == 'interactive':
      return f':{cmd}'
    return f'--{cmd}'

