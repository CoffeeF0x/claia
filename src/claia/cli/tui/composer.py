"""
Composer: the multiline input at the bottom of the app.

Enter submits; Shift+Enter inserts a newline where the terminal
reports it (Kitty keyboard protocol — Textual delivers the key as
``shift+enter``); Ctrl+J is the documented fallback newline for
terminals that cannot. Up/Down at an empty composer recall the
in-session submission history; any edit to a recalled entry drops
back to normal cursor movement. Paste is Textual-native
(bracketed). The widget never clears itself — the app clears it
once a submission is accepted, so a rejected submit keeps its text.
"""

# External dependencies
from typing import List, Optional

from textual import events
from textual.message import Message
from textual.widgets import TextArea



########################################################################
#                               CLASSES                                #
########################################################################
class Composer(TextArea):
  """Multiline text area that submits on Enter."""

  DEFAULT_CSS = """
  Composer {
    height: auto;
    min-height: 3;
    max-height: 8;
  }
  """

  class Submitted(Message):
    """Posted when the user presses Enter on non-empty text."""

    def __init__(self, composer: "Composer", text: str) -> None:
      super().__init__()
      self.composer = composer
      self.text = text

  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self._history: List[str] = []
    self._history_pos: Optional[int] = None

  # ── Key handling ─────────────────────────────────────────────────

  async def _on_key(self, event: events.Key) -> None:
    if event.key == "enter":
      event.stop()
      event.prevent_default()
      text = self.text.strip()
      if text:
        self.post_message(self.Submitted(self, text))
      return
    if event.key in ("shift+enter", "ctrl+j"):
      event.stop()
      event.prevent_default()
      start, end = self.selection
      # maintain_selection_offset=False mirrors keyboard-style edits:
      # the cursor lands just after the inserted newline.
      self.replace("\n", start, end, maintain_selection_offset=False)
      return
    if event.key == "up" and self._recall(-1):
      event.stop()
      event.prevent_default()
      return
    if event.key == "down" and self._recall(1):
      event.stop()
      event.prevent_default()
      return
    await super()._on_key(event)

  # ── History ──────────────────────────────────────────────────────

  def remember(self, text: str) -> None:
    """Record an accepted submission and reset history navigation."""
    if text and (not self._history or self._history[-1] != text):
      self._history.append(text)
    self._history_pos = None

  def _navigating(self) -> bool:
    """History applies at an empty composer or on an unedited recall."""
    if not self.text:
      return True
    return (
      self._history_pos is not None
      and self.text == self._history[self._history_pos]
    )

  def _recall(self, direction: int) -> bool:
    """Step through history; returns True when the key was consumed."""
    if not self._history or not self._navigating():
      return False
    if self._history_pos is None:
      if direction > 0:
        return False
      target = len(self._history) - 1
    else:
      target = self._history_pos + direction
    if target < 0:
      return True  # already at the oldest entry; swallow the key
    if target > len(self._history) - 1:
      self._set_text("")
      self._history_pos = None
      return True
    self._set_text(self._history[target])
    self._history_pos = target
    return True

  def _set_text(self, text: str) -> None:
    self.load_text(text)
    self.move_cursor(self.document.end)
