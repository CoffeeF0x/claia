"""
Action panel: the record of every action this session, newest
first. Hidden by default; toggled with Alt+A. Each record shows a
status glyph, the command as typed, and the full ``Result``
message/output — toasts are the notification, this is the record.
The panel overlays the right edge on its own layer, so toggling it
never reflows the transcript.
"""

# External dependencies
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Static

# Internal dependencies
from .actions import Action, ActionState



########################################################################
#                              CONSTANTS                               #
########################################################################
GLYPHS = {
  ActionState.PENDING: "·",
  ActionState.RUNNING: "…",
  ActionState.DONE: "✓",
  ActionState.FAILED: "✗",
}



########################################################################
#                               CLASSES                                #
########################################################################
class ActionRecord(Vertical):
  """One action's record: glyph + command line, then full output."""

  DEFAULT_CSS = """
  ActionRecord {
    height: auto;
    margin-bottom: 1;

    & > .action-title {
      color: $text-muted;
      text-style: bold;
    }
    &.-done > .action-title {
      color: $success;
    }
    &.-failed > .action-title {
      color: $error;
    }
    & > .action-output {
      color: $text-muted;
    }
  }
  """

  def __init__(self, action: Action, **kwargs):
    super().__init__(**kwargs)
    self.action = action

  def compose(self) -> ComposeResult:
    yield Static(classes="action-title")
    yield Static(classes="action-output")

  def on_mount(self) -> None:
    self.refresh_record()

  def refresh_record(self) -> None:
    # Pre-mount updates are safe to skip: on_mount re-renders from
    # the action's current state.
    if not self.is_mounted:
      return
    action = self.action
    for state in ActionState:
      self.set_class(state is action.state, f"-{state.value}")
    self.query_one(".action-title", Static).update(
      Text(f"{GLYPHS[action.state]} :{action.line}")
    )
    body = "\n".join(
      part for part in (action.message, action.output) if part
    )
    output = self.query_one(".action-output", Static)
    output.update(Text(body))
    output.display = bool(body)


class ActionPanel(VerticalScroll):
  """Scrollable newest-first list of action records."""

  DEFAULT_CSS = """
  ActionPanel {
    layer: actions;
    dock: right;
    width: 44;
    max-width: 80%;
    display: none;
    padding: 0 1;
    background: $panel;
    border-left: outer $border-blurred;

    &.-open {
      display: block;
    }
  }
  """

  def toggle(self) -> None:
    self.toggle_class("-open")

  def add_record(self, action: Action) -> None:
    """Mount a record for ``action`` at the top of the list."""
    first = self.children[0] if self.children else None
    self.mount(ActionRecord(action), before=first)

  def update_record(self, action: Action) -> None:
    """Re-render the record whose action changed state."""
    for record in self.query(ActionRecord):
      if record.action is action:
        record.refresh_record()
        return
