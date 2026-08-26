"""
Transcript pane: a scrolling list of plain-text blocks.

Phase-2 rendering is deliberately plain — role labels, message
text, and dim one-line notices. Turn widgets, markdown, and the
theme arrive in phase 3. Follow-tail uses Textual anchor
semantics: the pane stays pinned to the bottom while content
streams and releases the moment the user scrolls up (re-engaging
when they scroll back to the bottom).
"""

# External dependencies
from typing import Optional

from rich.text import Text
from textual.containers import VerticalScroll
from textual.widgets import Static



########################################################################
#                               CLASSES                                #
########################################################################
class Transcript(VerticalScroll):
  """Scrolling pane of role-prefixed plain-text transcript blocks.

  All mutation methods must be called from the UI thread. Streamed
  text accumulates into a live block that a notice (tool call,
  artifact) closes; the next delta then opens a fresh block, so tool
  markers land between the text spans they interrupted.
  """

  DEFAULT_CSS = """
  Transcript {
    height: 1fr;
    padding: 0 1;
  }
  Transcript > Static {
    width: 100%;
  }
  Transcript > .transcript-label {
    margin-top: 1;
  }
  Transcript > .transcript-label:first-child {
    margin-top: 0;
  }
  Transcript > .transcript-notice {
    text-style: dim;
  }
  """

  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self._live: Optional[Static] = None
    self._live_text = ""

  def on_mount(self) -> None:
    self.anchor()

  # ── Completed blocks ─────────────────────────────────────────────

  def add_message(self, label: str, text: str) -> None:
    """Append a finished message: a role label plus its content."""
    self._mount_label(label)
    if text:
      self.mount(Static(Text(text)))

  def add_notice(self, line: str) -> None:
    """Append one dim notice line; closes any live text block."""
    self.end_block()
    self.mount(Static(Text(line), classes="transcript-notice"))

  # ── Live streaming ───────────────────────────────────────────────

  def begin_turn(self, label: str) -> None:
    """Open a streamed turn under ``label``."""
    self._mount_label(label)

  def append_stream(self, text: str) -> None:
    """Append a text delta to the live block, creating it on demand."""
    if not text:
      return
    if self._live is None:
      self._live = Static()
      self._live_text = ""
      self.mount(self._live)
    self._live_text += text
    self._live.update(Text(self._live_text))

  def end_block(self) -> None:
    """Close the live text block (next delta opens a new one)."""
    self._live = None
    self._live_text = ""

  # ── Internals ────────────────────────────────────────────────────

  def _mount_label(self, label: str) -> None:
    self.end_block()
    self.mount(Static(Text(label), classes="transcript-label"))
