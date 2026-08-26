"""
The ledger: a full page recording every action this session,
newest first. Toggled with Alt+A (or ``:actions``); Escape returns
to the conversation.

Not a modal — a place. A vertical kintsugi seam spines the left
edge and carries the action lane's liveness (amber while a command
runs, red flash on failure); the heading counts the session's
actions; each record shows a status glyph, the command as typed, a
duration whisper, and the full ``Result`` message/output — toasts
are the notification, this is the record. Records whose result
declares ``format="markdown"`` render as markdown.

Actions live on the app (``app.actions``); the screen composes from
that list each time it opens and the app forwards state changes
while it is up, so the ledger itself keeps no state worth losing.
"""

# External dependencies
from typing import Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Markdown, Static

# Internal dependencies
from .actions import Action, ActionState
from .seam import Phase, Seam
from .turn import TurnLabel



########################################################################
#                              CONSTANTS                               #
########################################################################
GLYPHS = {
  ActionState.PENDING: "·",
  ActionState.RUNNING: "…",
  ActionState.DONE: "✓",
  ActionState.FAILED: "✗",
}

EMPTY_LINE = "Nothing on the books yet — :help opens the catalog."



########################################################################
#                               RECORD                                 #
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
    & > .action-note {
      color: $text-muted;
    }
    & > Markdown {
      margin: 0;
      padding: 0 0 0 2;
      background: transparent;
    }
  }
  """

  def __init__(self, action: Action, **kwargs):
    super().__init__(**kwargs)
    self.action = action
    self._markdown: Optional[Markdown] = None

  def compose(self) -> ComposeResult:
    yield Static(classes="action-title")
    yield Static(classes="action-note")

  def on_mount(self) -> None:
    self.refresh_record()

  def refresh_record(self) -> None:
    # Pre-compose updates are safe to skip: on_mount re-renders
    # from the action's current state. (``is_mounted`` is still
    # False inside on_mount for compose-time children, so gate on
    # the composed children instead.)
    if not self.children:
      return
    action = self.action
    for state in ActionState:
      self.set_class(state is action.state, f"-{state.value}")
    title = Text(f"{GLYPHS[action.state]} :{action.line}")
    if action.finished is not None:
      title.append(f"  {action.finished - action.created:.1f}s", "dim")
    self.query_one(".action-title", Static).update(title)

    markdown = action.format == "markdown" and bool(action.output)
    note = action.message if markdown else "\n".join(
      part for part in (action.message, action.output) if part
    )
    note_widget = self.query_one(".action-note", Static)
    note_widget.update(Text(note or ""))
    note_widget.display = bool(note)
    if markdown:
      if self._markdown is None:
        self._markdown = Markdown(action.output)
        self.mount(self._markdown)
      else:
        self._markdown.update(action.output)



########################################################################
#                               LEDGER                                 #
########################################################################
class Ledger(Screen):
  """Full-page, newest-first record of the session's actions."""

  BINDINGS = [
    Binding("escape", "dismiss", "Back", show=False),
    Binding("alt+a", "dismiss", "Back", show=False, priority=True),
  ]

  DEFAULT_CSS = """
  Ledger {
    layout: horizontal;
    background: $background;

    & > Seam {
      margin: 1 0;
    }
    & > .ledger-body {
      width: 1fr;
      padding: 1 1 0 2;

      & > TurnLabel {
        margin-bottom: 1;
      }
      & > .ledger-list {
        height: 1fr;
        scrollbar-gutter: stable;

        & > .ledger-empty {
          color: $text-muted;
        }
      }
      & > .ledger-footer {
        height: 1;
        color: $text-muted;
      }
    }
  }
  """

  def compose(self) -> ComposeResult:
    yield Seam(orientation="vertical", id="ledger-spine")
    with Vertical(classes="ledger-body"):
      yield TurnLabel("ACTIONS")
      with VerticalScroll(classes="ledger-list"):
        actions = self.app.actions
        if actions:
          for action in actions:
            yield ActionRecord(action)
        else:
          yield Static(EMPTY_LINE, classes="ledger-empty")
      yield Static("esc back", classes="ledger-footer")

  def on_mount(self) -> None:
    self._refresh_summary()
    running = any(
      a.state is ActionState.RUNNING for a in self.app.actions
    )
    if running:
      self.query_one(Seam).set_phase(Phase.TOOL)

  def record_update(self, action: Action) -> None:
    """Re-render the record whose action changed state."""
    for record in self.query(ActionRecord):
      if record.action is action:
        record.refresh_record()
        break
    self._refresh_summary()
    # The lane is serial, so this action alone decides the spine.
    spine = self.query_one(Seam)
    if action.state is ActionState.RUNNING:
      spine.set_phase(Phase.TOOL)
    else:
      spine.set_phase(Phase.IDLE)
      if action.state is ActionState.FAILED:
        spine.flash("error")

  def _refresh_summary(self) -> None:
    actions = self.app.actions
    if not actions:
      return
    failed = sum(1 for a in actions if a.state is ActionState.FAILED)
    meta = f"{len(actions)} run"
    if failed:
      meta += f" · {failed} failed"
    self.query_one(TurnLabel).set_meta(meta)
