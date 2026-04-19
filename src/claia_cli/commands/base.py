"""
Base command class for CLAIA CLI commands.
"""

import logging
from typing import List, Optional, Any
from abc import ABC, abstractmethod

from claia_core.results import Result
from claia.registry import Registry


class BaseCommand(ABC):
  """Base class for all CLAIA CLI commands."""
  
  def __init__(self, registry: Registry, settings: Any, current_mode: str = 'interactive'):
    self.registry = registry
    self.settings = settings
    self._current_mode = current_mode
    self.logger = logging.getLogger(self.__class__.__name__)
  
  @abstractmethod
  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """Execute the command with the given arguments."""
    pass
  
  def get_help_prefix(self) -> str:
    """Get the command prefix (':' for interactive, '--' for CLI)."""
    return ':' if self._current_mode == 'interactive' else '--'
  
  def format_command(self, cmd: str) -> str:
    """Format a command string with the appropriate prefix."""
    return f':{cmd}' if self._current_mode == 'interactive' else f'--{cmd}'
