"""
Hook specifications for tool-calling patterns.

A pattern plugin is responsible for detecting tool call invocations
inside content (e.g., tags, JSON blocks, function_call markers).
"""

import pluggy
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class PatternInfo:
  name: str
  title: str
  description: str
  opening_token: str  # Token that starts a tool call
  closing_token: str  # Token that ends a tool call
  prompt_template: Optional[str] = None  # Optional system/tool prompt template


hookspec = pluggy.HookspecMarker("claia_tool_patterns")


@dataclass
class ToolCallMatch:
  # Inclusive start index and exclusive end index for replacement
  start_index: int
  end_index: int
  tool_name: str
  parameters: Dict[str, Any]
  raw: Optional[str] = None


class PatternHooks:
  """Hook specifications for tool-calling pattern plugins."""

  @hookspec
  def get_pattern_info(self) -> PatternInfo:
    """
    Return information about this pattern plugin.
    """

  @hookspec
  def find_tool_calls(self, content: str, conversation, settings=None) -> List[ToolCallMatch]:
    """
    Find tool call invocations in the given content.
    Return a list of ToolCallMatch, sorted by start_index.
    """
