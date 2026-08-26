"""
The kintsugi seam: a one-cell crack carrying ambient liveness.

The crack is a deterministic pattern of line characters (seeded per
length) with occasional thick veins. At rest it sits in the resting
border color with the veins in dimmed gold. While its subject works,
glints of gold travel the crack — warm amber during tool or action
execution — and a failure or cancel flashes the whole line in the
matching semantic color before decaying back to rest.

Two orientations of the same widget: the horizontal seam between
transcript and composer follows the bound track; the vertical spine
on the ledger page follows the action lane.

Pure display: owners push :class:`Phase` changes and flashes; the
widget owns its own timer and pauses it whenever there is nothing
left to animate. When Textual's animation level is ``none`` the
seam renders static state colors instead of moving.
"""

# External dependencies
import random
from enum import Enum
from typing import Optional

from rich.style import Style
from rich.text import Text
from textual.color import Color
from textual.timer import Timer
from textual.widget import Widget



########################################################################
#                              CONSTANTS                               #
########################################################################
TICK = 0.08          # seconds between animation frames
SPEED = 1.6          # cells a glint travels per frame
GLINTS = 2           # glints on the crack at once
REACH = 7.0          # falloff radius around a glint, in cells
FLASH_DECAY = 0.09   # flash intensity lost per frame

VEINS = "━┃"         # crack characters that read as gold veins

# (vein, gap, line) character sets per orientation.
CHARS = {
  "horizontal": ("━", "╌", "─"),
  "vertical": ("┃", "╎", "│"),
}


class Phase(Enum):
  """What the seam's subject is doing, as far as display cares."""
  IDLE = "idle"
  STREAMING = "streaming"
  TOOL = "tool"



########################################################################
#                              FUNCTIONS                               #
########################################################################
def crack_pattern(length: int, orientation: str = "horizontal") -> str:
  """A deterministic crack for ``length`` cells.

  Seeded by length so resizes are stable: runs of plain line broken
  by short hairline gaps and thick gold veins.
  """
  vein, gap, line = CHARS[orientation]
  rng = random.Random(length * 7919)
  cells = []
  while len(cells) < length:
    roll = rng.random()
    if roll < 0.10:
      cells.extend(vein * rng.randint(2, 4))
    elif roll < 0.22:
      cells.extend(gap * rng.randint(1, 2))
    else:
      cells.extend(line * rng.randint(4, 9))
  return "".join(cells[:length])



########################################################################
#                                 SEAM                                 #
########################################################################
class Seam(Widget):
  """One cell-wide line of crack; horizontal or vertical."""

  DEFAULT_CSS = """
  Seam {
    height: 1;
    margin: 0 1;

    &.-vertical {
      width: 1;
      height: 100%;
      margin: 0;
    }
  }
  """

  def __init__(self, orientation: str = "horizontal", **kwargs):
    super().__init__(**kwargs)
    self.orientation = orientation
    self.phase = Phase.IDLE
    self._pattern = ""
    self._offset = 0.0
    self._flash_kind: Optional[str] = None
    self._flash = 0.0
    self._timer: Optional[Timer] = None
    if orientation == "vertical":
      self.add_class("-vertical")

  def on_mount(self) -> None:
    self._timer = self.set_interval(TICK, self._tick, pause=True)
    self._wake()

  # ── State pushed by the switchboard ──────────────────────────────

  def set_phase(self, phase: Phase) -> None:
    if phase is self.phase:
      return
    self.phase = phase
    self._wake()
    self.refresh()

  def flash(self, kind: str) -> None:
    """Flood the crack in a semantic color: ``error`` or ``warning``."""
    self._flash_kind = kind
    self._flash = 1.0
    self._wake()
    self.refresh()

  # ── Animation ────────────────────────────────────────────────────

  def _animated(self) -> bool:
    return getattr(self.app, "animation_level", "full") != "none"

  def _wake(self) -> None:
    if self._timer is None or not self._animated():
      return
    if self.phase is not Phase.IDLE or self._flash > 0:
      self._timer.resume()

  def _tick(self) -> None:
    length = max(self._length(), 1)
    self._offset = (self._offset + SPEED) % length
    if self._flash > 0:
      self._flash = max(0.0, self._flash - FLASH_DECAY)
    if self.phase is Phase.IDLE and self._flash <= 0:
      self._timer.pause()
    self.refresh()

  def _length(self) -> int:
    if self.orientation == "vertical":
      return self.size.height
    return self.size.width

  # ── Rendering ────────────────────────────────────────────────────

  def render(self) -> Text:
    length = self._length()
    if length <= 0:
      return Text("")
    if len(self._pattern) != length:
      self._pattern = crack_pattern(length, self.orientation)

    theme = self.app.theme_variables
    base = Color.parse(theme["border-blurred"])
    gold = Color.parse(theme["primary"])
    vein = gold.blend(base, 0.55)
    core, tip = self._glint_colors(theme, gold)
    flash = (
      Color.parse(theme[self._flash_kind])
      if self._flash_kind and self._flash > 0 else None
    )

    active = self.phase is not Phase.IDLE
    animated = self._animated()
    if active:
      # A charged crack: the whole line lifts toward the state
      # color, the veins carry it fully, glints ride on top.
      base = base.blend(core, 0.3)
      vein = core
    centers = [
      (self._offset + k * length / GLINTS) % length
      for k in range(GLINTS)
    ]

    vertical = self.orientation == "vertical"
    text = Text()
    for i, char in enumerate(self._pattern):
      if vertical and i:
        text.append("\n")
      color = vein if char in VEINS else base
      if active and animated:
        glow = self._glow(i, centers, length)
        if glow >= 0.95:
          color = tip
        elif glow > 0:
          color = color.blend(tip, glow * 0.8)
      if flash is not None:
        color = color.blend(flash, min(self._flash, 1.0) * 0.85)
      text.append(char, Style(color=color.rich_color))
    return text

  def _glint_colors(self, theme, gold: Color):
    if self.phase is Phase.TOOL:
      amber = Color.parse(theme["warning"])
      return amber, amber.lighten(0.12)
    return gold, Color.parse(theme["secondary"])

  @staticmethod
  def _glow(cell: int, centers, length: int) -> float:
    """0..1 glint intensity for a cell (circular distance falloff)."""
    glow = 0.0
    for center in centers:
      distance = abs(cell - center)
      distance = min(distance, length - distance)
      if distance < REACH:
        glow = max(glow, 1.0 - distance / REACH)
    return glow
