"""
Base command class for CLAIA CLI commands.
"""

import logging
from typing import List, Optional, Any
from abc import ABC, abstractmethod

from ...core.results import Result
from ...framework.registry import Registry


class BaseCommand(ABC):
  """Base class for all CLAIA CLI commands."""
  
  def __init__(self, registry: Registry, settings: Any):
    self.registry = registry
    self.settings = settings
    self.logger = logging.getLogger(self.__class__.__name__)
  
  @abstractmethod
  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """Execute the command with the given arguments."""
    pass
  
  def get_help_prefix(self) -> str:
    """Prefix for presenting commands in usage text."""
    return 'claia '
  
  def format_command(self, cmd: str) -> str:
    """Present a command in the leading subcommand form."""
    return f'claia {cmd}'
