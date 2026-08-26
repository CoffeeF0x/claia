"""
Help card: the key map on a modal overlay.

F1 (or Alt+H where terminals eat F-keys) toggles it from the app;
Esc closes. This is where the long key hints live so the status bar
can stay a one-line instrument cluster — and it points at ``:help``
for the command surface rather than duplicating it.
"""

# External dependencies
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static



########################################################################
#                              CONSTANTS                               #
########################################################################
ROWS = [
  ("enter", "send the message"),
  ("shift+enter / ctrl+j", "newline"),
  ("up / down", "history at an empty composer"),
  ("esc", "cancel the streaming turn"),
  ("alt+n / alt+p", "next / previous track"),
  ("alt+a", "open the action ledger"),
  ("f1 / alt+h", "this card"),
  ("ctrl+q / alt+q", "quit"),
]

FOOTER = "Commands live behind ':' — :help lists them all."



########################################################################
#                               CLASSES                                #
########################################################################
class HelpScreen(ModalScreen):
  """A dismissable card listing the keys and their fallbacks."""

  BINDINGS = [
    Binding("escape", "close_help", "Close", show=False, id="help-close"),
    Binding("f1", "close_help", "Close", show=False, id="help-close-f1"),
    Binding("alt+h", "close_help", "Close", show=False,
            id="help-close-alt"),
  ]

  DEFAULT_CSS = """
  HelpScreen {
    align: center middle;
    background: $background 60%;

    & > .help-card {
      width: 62;
      max-width: 90%;
      height: auto;
      padding: 1 2;
      background: $panel;
      border: round $primary;

      & > .help-title {
        color: $primary;
        text-style: bold;
        margin-bottom: 1;
      }
      & > .help-footer {
        color: $text-muted;
        margin-top: 1;
      }
    }
  }
  """

  def compose(self) -> ComposeResult:
    pad = max(len(key) for key, _ in ROWS) + 2
    rows = Text()
    for index, (key, description) in enumerate(ROWS):
      if index:
        rows.append("\n")
      rows.append(key.ljust(pad), "bold")
      rows.append(description)
    yield Vertical(
      Static(Text("◆ KEYS"), classes="help-title"),
      Static(rows, classes="help-rows"),
      Static(Text(FOOTER), classes="help-footer"),
      classes="help-card",
    )

  def action_close_help(self) -> None:
    self.dismiss()
