"""
Transcript pane: a scrolling list of user blocks and turn views.

User messages are transcript-level label blocks (``YOU`` + text);
assistant turns are ``TurnView`` widgets fed block events by the app
(paced when live, replayed instantly on reload). Follow-tail uses
Textual anchor semantics: pinned to the bottom while content grows,
released when the user scrolls up, re-engaged at the bottom.
"""

# External dependencies
from rich.text import Text
from textual.containers import VerticalScroll
from textual.widgets import Static

# Internal dependencies
from .turn import TurnView



########################################################################
#                               CLASSES                                #
########################################################################
class Transcript(VerticalScroll):
  """Scrolling pane of transcript blocks; mutate on the UI thread."""

  DEFAULT_CSS = """
  Transcript {
    height: 1fr;
    padding: 0 1;

    & > .user-label {
      margin-top: 1;
      color: $user-label;
      text-style: bold;
    }
    & > .user-label:first-child {
      margin-top: 0;
    }
    & > TurnView:first-child {
      margin-top: 0;
    }
  }
  """

  def on_mount(self) -> None:
    self.anchor()

  def add_user(self, text: str) -> None:
    """Append a user message: the YOU micro-label plus its text."""
    self.mount(Static(Text("YOU"), classes="user-label"))
    if text:
      self.mount(Static(Text(text), classes="user-text"))

  async def begin_turn(self, label: str) -> TurnView:
    """Mount and return a fresh assistant turn view.

    Awaits the mount so the composed label lands before any block
    events mount segments into the view.
    """
    view = TurnView(label)
    await self.mount(view)
    return view
