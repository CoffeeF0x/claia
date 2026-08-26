"""
Status bar: one line of session context and task state.

Shows the active model, agent, and conversation on the left and
the task state (idle/streaming) plus the last turn's usage and
duration on the right. The app pushes updates; the bar renders.
"""

# External dependencies
from typing import Optional

from rich.text import Text
from textual.widgets import Static



########################################################################
#                               CLASSES                                #
########################################################################
class StatusBar(Static):
  """Single-line status readout for the app."""

  DEFAULT_CSS = """
  StatusBar {
    dock: bottom;
    height: 1;
    padding: 0 1;
    background: $panel;
  }
  """

  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.model: Optional[str] = None
    self.agent: Optional[str] = None
    self.conversation: Optional[str] = None
    self.state = "idle"
    self.last_turn: Optional[str] = None

  def set_context(
    self,
    model: Optional[str],
    agent: Optional[str],
    conversation: Optional[str],
  ) -> None:
    self.model = model
    self.agent = agent
    self.conversation = conversation
    self._render_line()

  def set_state(self, state: str) -> None:
    """Task state: ``idle`` or ``streaming``."""
    self.state = state
    self._render_line()

  def set_last_turn(self, summary: Optional[str]) -> None:
    """Usage/duration summary from the last turn's StreamEnd."""
    self.last_turn = summary
    self._render_line()

  def _render_line(self) -> None:
    parts = [
      f"model: {self.model or '-'}",
      f"agent: {self.agent or '-'}",
      f"conversation: {self.conversation or '-'}",
      self.state,
    ]
    if self.last_turn:
      parts.append(self.last_turn)
    self.update(Text("  |  ".join(parts)))
