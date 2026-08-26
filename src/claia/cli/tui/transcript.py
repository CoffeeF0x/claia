"""
Transcript pane: a scrolling list of user blocks and turn views.

User messages are transcript-level label blocks (``YOU`` + text);
assistant turns are ``TurnView`` widgets fed block events by the app
(paced when live, replayed instantly on reload). An empty transcript
centers a small greeting in the brand voice, dismissed by the first
content. Follow-tail uses Textual anchor semantics: pinned to the
bottom while content grows, released when the user scrolls up,
re-engaged at the bottom.
"""

# External dependencies
from rich.text import Text
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Static

# Internal dependencies
from .turn import TurnView



########################################################################
#                              CONSTANTS                               #
########################################################################
GREETING_TITLE = "◆ CLAIA"
GREETING_BODY = "Nothing here yet. Want to change that?"
GREETING_HINTS = "Enter sends · :help commands · F1 keys"



########################################################################
#                               CLASSES                                #
########################################################################
class Transcript(VerticalScroll):
  """Scrolling pane of transcript blocks; mutate on the UI thread."""

  DEFAULT_CSS = """
  Transcript {
    height: 1fr;
    /* The stable gutter is the right-hand breathing room: content
       never shifts when the (track-invisible) scrollbar appears. */
    padding: 0 0 0 1;
    scrollbar-gutter: stable;

    &.-empty {
      align: center middle;
    }
    & > .transcript-greeting {
      width: 100%;
      height: auto;

      & > .greeting-title {
        width: 100%;
        text-align: center;
        color: $primary;
        text-style: bold;
      }
      & > .greeting-body {
        width: 100%;
        text-align: center;
        margin-top: 1;
      }
      & > .greeting-hints {
        width: 100%;
        text-align: center;
        margin-top: 1;
        color: $text-muted;
      }
    }
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
    # Anchoring while the greeting is centered drags the scroll
    # negative and pins the greeting to the bottom; follow-tail
    # engages once real content exists instead.
    if not self.children:
      self.add_class("-empty")
      self.mount(Vertical(
        Static(Text(GREETING_TITLE), classes="greeting-title"),
        Static(Text(GREETING_BODY), classes="greeting-body"),
        Static(Text(GREETING_HINTS), classes="greeting-hints"),
        classes="transcript-greeting",
      ))
    else:
      self.anchor()

  def add_user(self, text: str) -> None:
    """Append a user message: the YOU micro-label plus its text."""
    self._dismiss_greeting()
    self.mount(Static(Text("YOU"), classes="user-label"))
    if text:
      self.mount(Static(Text(text), classes="user-text"))

  async def begin_turn(self, label: str) -> TurnView:
    """Mount and return a fresh assistant turn view.

    Awaits the mount so the composed label lands before any block
    events mount segments into the view.
    """
    self._dismiss_greeting()
    view = TurnView(label)
    await self.mount(view)
    return view

  def _dismiss_greeting(self) -> None:
    if self.has_class("-empty"):
      self.remove_class("-empty")
      for node in self.query(".transcript-greeting"):
        node.remove()
      self.anchor()
