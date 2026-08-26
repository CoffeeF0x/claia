"""
Status bar: one line of session context, task state, and key hints.

Left side: active model, agent, conversation, idle/streaming state,
and the last turn's usage/duration. Right side: curated key hints so
the non-obvious keys (Ctrl+J newline) are discoverable in the UI —
this is the app's one bottom bar; there is no Footer widget. The app
pushes updates; the bar renders.
"""

# External dependencies
from typing import Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static



########################################################################
#                              CONSTANTS                               #
########################################################################
KEY_HINTS = "^J newline · Esc cancel · ^Q quit"



########################################################################
#                               CLASSES                                #
########################################################################
class StatusBar(Horizontal):
  """Single-line status readout with right-aligned key hints."""

  DEFAULT_CSS = """
  StatusBar {
    dock: bottom;
    height: 1;
    padding: 0 1;
    background: $panel;

    & > .status-line {
      width: 1fr;
      color: $foreground;
    }
    & > .status-hints {
      width: auto;
      color: $text-muted;
    }
  }
  """

  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.model: Optional[str] = None
    self.agent: Optional[str] = None
    self.conversation: Optional[str] = None
    self.state = "idle"
    self.last_turn: Optional[str] = None

  def compose(self) -> ComposeResult:
    yield Static(classes="status-line")
    yield Static(Text(KEY_HINTS), classes="status-hints")

  def on_mount(self) -> None:
    self._render_line()

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
    if not self.is_mounted:
      return
    parts = [
      f"model: {self.model or '-'}",
      f"agent: {self.agent or '-'}",
      f"conversation: {self.conversation or '-'}",
      self.state,
    ]
    if self.last_turn:
      parts.append(self.last_turn)
    self.query_one(".status-line", Static).update(
      Text("  |  ".join(parts))
    )
