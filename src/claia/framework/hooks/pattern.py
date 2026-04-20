"""
Pluggy hookspecs for tool-pattern plugins.

These specs mirror ``BasePattern`` in
``claia.core.tools.patterns.base``.
"""

import pluggy
from typing import List

from claia.core.plugins.base import PatternInfo, ToolCallMatch


hookspec = pluggy.HookspecMarker("claia_tool_patterns")


class PatternHooks:
  """Hook specifications for tool-pattern plugins."""

  @hookspec
  def get_pattern_info(self) -> PatternInfo:
    """Return metadata describing this pattern."""

  @hookspec
  def find_tool_calls(self, content: str, conversation, settings=None) -> List[ToolCallMatch]:
    """Return all tool-call invocations in ``content`` sorted by start index."""


__all__ = ["PatternHooks", "PatternInfo", "ToolCallMatch"]
