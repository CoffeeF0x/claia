"""
Abstract base class for tool-module plugins.

A tool module groups one or more callable tools (commands) under a
common namespace. Each tool is described by a ``ToolDefinition`` that
declares its callable, description, and arguments.

Subclasses declare their metadata via a class-level ``info`` attribute
so plugin discovery does not have to instantiate the plugin.
"""

from abc import ABC, abstractmethod
from typing import ClassVar, Dict

from ...plugins.base import ToolModuleInfo, ToolDefinition


class BaseToolModule(ABC):
  """Contract for tool-module plugins."""

  info: ClassVar[ToolModuleInfo]

  def get_module_info(self) -> ToolModuleInfo:
    """Return metadata describing this tool module.

    Default implementation returns the class-level ``info`` attribute.
    """
    return type(self).info

  @abstractmethod
  def get_module_tools(self) -> Dict[str, ToolDefinition]:
    """Return the tools provided by this module keyed by tool name."""
