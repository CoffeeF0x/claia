"""
Status bar: the instrument cluster. One line, glyphs over prose.

Left side, dynamic segments first so clipping on narrow terminals
eats the whispers rather than the instruments: identity
(``◆ agent · model``), a braille spinner with elapsed time while
the bound track works (gold while streaming, amber during a tool
call), track dots when more than one track exists (gold = bound,
spinner = hidden and streaming, teal = unseen completion, muted =
idle), an ``✗ action`` marker while the lane's last command
failed, then the conversation title and the last turn's compact
usage as muted whispers. Right side: the three key hints that
matter; the rest live on the F1 card. The app pushes updates; the
bar renders and owns its own spinner timer, paused whenever
nothing is busy. Colors resolve through CSS component classes so
every theme (including Textual's ``auto`` shades) just works.
"""

# External dependencies
import time
from dataclasses import dataclass
from typing import List, Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.timer import Timer
from textual.widget import Widget
from textual.widgets import Static

# Internal dependencies
from .seam import Phase



########################################################################
#                              CONSTANTS                               #
########################################################################
KEY_HINTS = "F1 keys · M-a actions · ^Q quit"
SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
TICK = 0.1


@dataclass(frozen=True)
class TrackDot:
  """One track's state, as far as the dot row cares."""
  bound: bool
  busy: bool
  unseen: bool



########################################################################
#                              STATUS LINE                             #
########################################################################
class StatusLine(Widget):
  """The cluster's renderer; reads state from its owning bar."""

  COMPONENT_CLASSES = {
    "statusline--gold",
    "statusline--muted",
    "statusline--tool",
    "statusline--busy",
    "statusline--unseen",
    "statusline--failed",
  }

  DEFAULT_CSS = """
  StatusLine {
    width: 1fr;
    height: 1;
    color: $foreground;
  }
  StatusLine > .statusline--gold {
    color: $primary;
    text-style: bold;
  }
  StatusLine > .statusline--muted {
    color: $text-muted;
  }
  StatusLine > .statusline--tool {
    color: $warning;
  }
  StatusLine > .statusline--busy {
    color: $secondary;
  }
  StatusLine > .statusline--unseen {
    color: $user-label;
  }
  StatusLine > .statusline--failed {
    color: $error;
  }
  """

  def __init__(self, bar: "StatusBar", **kwargs):
    super().__init__(**kwargs)
    self._bar = bar

  def render(self) -> Text:
    bar = self._bar
    gold = self.get_component_rich_style("statusline--gold")
    muted = self.get_component_rich_style("statusline--muted")
    line = Text(no_wrap=True, overflow="crop")

    line.append("◆ ", gold)
    if bar.agent:
      line.append(bar.agent)
    if bar.agent and bar.model:
      line.append(" · ", muted)
    if bar.model:
      line.append(bar.model, muted)

    if bar.phase is not Phase.IDLE:
      spin = (
        "statusline--tool" if bar.phase is Phase.TOOL
        else "statusline--gold"
      )
      line.append("  ")
      line.append(bar.spin, self.get_component_rich_style(spin))
      if bar.since is not None:
        line.append(f" {bar.elapsed}", muted)

    if len(bar.dots) > 1:
      line.append("  ")
      for i, dot in enumerate(bar.dots):
        if i:
          line.append(" ")
        if dot.bound:
          line.append("●", gold)
        elif dot.busy:
          line.append(
            bar.spin, self.get_component_rich_style("statusline--busy"),
          )
        elif dot.unseen:
          line.append(
            "●", self.get_component_rich_style("statusline--unseen"),
          )
        else:
          line.append("○", muted)

    if bar.action_failed:
      line.append("  ")
      line.append(
        "✗ action", self.get_component_rich_style("statusline--failed"),
      )

    if bar.conversation:
      line.append("  ")
      line.append(bar.conversation, muted)
    if bar.last_turn:
      line.append("  ")
      line.append(bar.last_turn, muted)
    return line



########################################################################
#                              STATUS BAR                              #
########################################################################
class StatusBar(Horizontal):
  """Single-line instrument cluster with right-aligned key hints."""

  DEFAULT_CSS = """
  StatusBar {
    dock: bottom;
    height: 1;
    padding: 0 1;
    background: $panel;

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
    self.phase = Phase.IDLE
    self.since: Optional[float] = None
    self.dots: List[TrackDot] = []
    self.last_turn: Optional[str] = None
    self.action_failed = False
    self._frame = 0
    self._line: Optional[StatusLine] = None
    self._timer: Optional[Timer] = None

  @property
  def state(self) -> str:
    """The bound track's coarse state: ``idle`` or ``streaming``."""
    return "idle" if self.phase is Phase.IDLE else "streaming"

  @property
  def spin(self) -> str:
    return SPINNER[self._frame % len(SPINNER)]

  @property
  def elapsed(self) -> str:
    seconds = max(0, int(time.time() - (self.since or 0)))
    if seconds < 60:
      return f"{seconds}s"
    return f"{seconds // 60}m{seconds % 60:02d}s"

  def compose(self) -> ComposeResult:
    self._line = StatusLine(self, classes="status-line")
    yield self._line
    yield Static(Text(KEY_HINTS), classes="status-hints")

  def on_mount(self) -> None:
    self._timer = self.set_interval(TICK, self._tick, pause=True)
    self._ensure_ticker()

  # ── State pushed by the app ──────────────────────────────────────

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

  def set_activity(self, phase: Phase, since: Optional[float]) -> None:
    """Bound track's phase plus its task's start time."""
    self.phase = phase
    self.since = since if phase is not Phase.IDLE else None
    self._ensure_ticker()
    self._render_line()

  def set_tracks(self, dots: List[TrackDot]) -> None:
    """All tracks' dot states, in creation order."""
    self.dots = dots
    self._ensure_ticker()
    self._render_line()

  def set_last_turn(self, summary: Optional[str]) -> None:
    """Compact usage/duration from the last turn's StreamEnd."""
    self.last_turn = summary
    self._render_line()

  def set_action_failed(self, failed: bool) -> None:
    """Marker for the action lane's most recent outcome."""
    self.action_failed = failed
    self._render_line()

  # ── Spinner timer ────────────────────────────────────────────────

  def _animated(self) -> bool:
    return getattr(self.app, "animation_level", "full") != "none"

  def _ensure_ticker(self) -> None:
    if self._timer is None:
      return
    busy = self.phase is not Phase.IDLE or any(d.busy for d in self.dots)
    if busy and self._animated():
      self._timer.resume()
    else:
      self._timer.pause()

  def _tick(self) -> None:
    self._frame += 1
    self._render_line()

  # ── Rendering ────────────────────────────────────────────────────

  def _render_line(self) -> None:
    if self._line is not None and self._line.is_mounted:
      self._line.refresh()
