"""
Abstract base class for tool-pattern plugins.

A pattern locates tool-call invocations inside text content (e.g., custom
tags, JSON blocks, function-call markers) and returns a list of
``ToolCallMatch`` objects with the spans to replace.

Subclasses declare their metadata via a class-level ``info`` attribute
so plugin discovery does not have to instantiate the plugin.
"""

from abc import ABC, abstractmethod
from typing import ClassVar, List

from ...plugins.base import PatternInfo, ToolCallMatch


class BasePattern(ABC):
  """Contract for tool-pattern plugins."""

  info: ClassVar[PatternInfo]

  def get_pattern_info(self) -> PatternInfo:
    """Return metadata describing this pattern (including delimiters).

    Default implementation returns the class-level ``info`` attribute.
    """
    return type(self).info

  @abstractmethod
  def find_tool_calls(self, content: str, conversation, settings=None) -> List[ToolCallMatch]:
    """Return all tool-call invocations found in ``content``, sorted by start index."""
