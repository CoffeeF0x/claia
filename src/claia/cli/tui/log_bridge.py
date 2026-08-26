"""
Logging ownership while the TUI runs.

The app owns the terminal, so the root logger must not write to
the console. ``install`` strips console stream handlers (file
handlers stay untouched — INFO/DEBUG keep flowing to file per
settings) and attaches a forwarding handler that marshals
WARNING-and-up records into the app as toast notifications.
``restore`` puts everything back on exit; one-shot paths never
see any of this.

Records can be emitted from any thread (worker callbacks, plugin
internals); the handler crosses into the UI loop with a posted
message, which Textual makes thread-safe.
"""

# External dependencies
import logging
from typing import List, Tuple

from textual.message import Message



########################################################################
#                               MESSAGES                               #
########################################################################
class LogNotice(Message):
  """A WARNING+ log record headed for a toast."""

  def __init__(self, text: str, severity: str) -> None:
    super().__init__()
    self.text = text
    self.severity = severity



########################################################################
#                               CLASSES                                #
########################################################################
class UiLogHandler(logging.Handler):
  """Forward WARNING+ records into the app as ``LogNotice``s."""

  def __init__(self, app) -> None:
    super().__init__(level=logging.WARNING)
    self._app = app

  def emit(self, record: logging.LogRecord) -> None:
    try:
      severity = "error" if record.levelno >= logging.ERROR else "warning"
      self._app.post_message(LogNotice(record.getMessage(), severity))
    except Exception:
      self.handleError(record)



########################################################################
#                              FUNCTIONS                               #
########################################################################
def install(app) -> Tuple[List[logging.Handler], UiLogHandler]:
  """Take over console logging for the app's lifetime.

  Returns ``(removed_handlers, ui_handler)`` for :func:`restore`.
  """
  root = logging.getLogger()
  removed = [
    handler for handler in root.handlers
    if isinstance(handler, logging.StreamHandler)
    and not isinstance(handler, logging.FileHandler)
  ]
  for handler in removed:
    root.removeHandler(handler)
  ui_handler = UiLogHandler(app)
  root.addHandler(ui_handler)
  return removed, ui_handler


def restore(removed: List[logging.Handler], ui_handler: UiLogHandler) -> None:
  """Detach the forwarding handler and re-add the console handlers."""
  root = logging.getLogger()
  root.removeHandler(ui_handler)
  for handler in removed:
    if handler not in root.handlers:
      root.addHandler(handler)
