"""
Abstract base class for tool-module plugins.

A tool module groups one or more callable tools (commands) under a
common namespace. Each tool is described by a ``ToolDefinition`` that
declares its callable, description, and arguments.
"""

from abc import ABC, abstractmethod
from typing import Dict

from ...plugins.base import ToolModuleInfo, ToolDefinition


class BaseToolModule(ABC):
  """Contract for tool-module plugins."""

  @abstractmethod
  def get_module_info(self) -> ToolModuleInfo:
    """Return metadata describing this tool module."""

  @abstractmethod
  def get_module_tools(self) -> Dict[str, ToolDefinition]:
    """Return the tools provided by this module keyed by tool name."""
