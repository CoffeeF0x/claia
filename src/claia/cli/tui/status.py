"""
Status bar: one line of session context, task state, and key hints.

Left side: active model, agent, conversation, ``track i/N`` when
more than one track exists, the bound track's idle/streaming
state, an unseen-completion badge (``●2``) when hidden tracks
finished, the last turn's usage/duration, and a ``✗ action``
marker while the action lane's most recent command failed. Right
side: curated key hints so the non-obvious keys are discoverable
in the UI — this is the app's one bottom bar; there is no Footer
widget. The app pushes updates; the bar renders.
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
# Kept short: the hints share one line with the status segments,
# and a long hint block clips the track/unseen badges on narrow
# terminals.
KEY_HINTS = "M-a actions · M-n/p track · ^Q quit"



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
    self.track_index = 1
    self.track_count = 1
    self.unseen = 0
    self.action_failed = False

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
    """Bound track's task state: ``idle`` or ``streaming``."""
    self.state = state
    self._render_line()

  def set_last_turn(self, summary: Optional[str]) -> None:
    """Usage/duration summary from the last turn's StreamEnd."""
    self.last_turn = summary
    self._render_line()

  def set_tracks(self, index: int, count: int) -> None:
    """Bound track's 1-based position; shown only when count > 1."""
    self.track_index = index
    self.track_count = count
    self._render_line()

  def set_unseen(self, count: int) -> None:
    """How many hidden tracks completed since they were last bound."""
    self.unseen = count
    self._render_line()

  def set_action_failed(self, failed: bool) -> None:
    """Marker for the action lane's most recent outcome."""
    self.action_failed = failed
    self._render_line()

  def _render_line(self) -> None:
    if not self.is_mounted:
      return
    # The line clips right-first on narrow terminals, so the
    # dynamic segments (track, badge, state) come before the
    # conversation label and usage summary.
    parts = [
      f"model: {self.model or '-'}",
      f"agent: {self.agent or '-'}",
    ]
    if self.track_count > 1:
      parts.append(f"track {self.track_index}/{self.track_count}")
    if self.unseen:
      parts.append(f"●{self.unseen}")
    parts.append(self.state)
    if self.action_failed:
      parts.append("✗ action")
    parts.append(f"conversation: {self.conversation or '-'}")
    if self.last_turn:
      parts.append(self.last_turn)
    self.query_one(".status-line", Static).update(
      Text("  |  ".join(parts))
    )
