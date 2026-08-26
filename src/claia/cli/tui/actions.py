"""
Actions: the serial lane for user intent that is not chat.

An ``Action`` records one command-line unit of intent — the line,
its source, state, the ``Result`` message/output, timestamps. The
``ActionLane`` executes actions in order on one worker thread via
``Commands.run`` (commands are near-instant and touch shared
settings/registry state; racing them buys nothing) and marshals
each transition back into the UI loop as a posted message. The
``:`` prefix is TUI-only dressing — tokens after it reach
``Commands.run`` untouched.
"""

# External dependencies
import logging
import queue
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from textual.message import Message

# Internal dependencies
from ...core.results import Result



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                                ACTION                                #
########################################################################
class ActionState(Enum):
  PENDING = "pending"
  RUNNING = "running"
  DONE = "done"
  FAILED = "failed"


@dataclass
class Action:
  """One unit of user intent headed for ``Commands.run``."""

  line: str
  tokens: List[str]
  source: str = "composer"
  state: ActionState = ActionState.PENDING
  message: Optional[str] = None
  output: Optional[str] = None
  format: str = "text"
  created: float = field(default_factory=time.time)
  finished: Optional[float] = None

  def start(self) -> None:
    self.state = ActionState.RUNNING

  def finish(self, result: Result) -> None:
    self.state = (
      ActionState.DONE if result.is_success() else ActionState.FAILED
    )
    self.message = result.get_message()
    data = result.get_data()
    self.output = str(data) if data is not None else None
    self.format = result.format
    self.finished = time.time()

  def fail(self, message: str) -> None:
    """Refuse or fail the action without running it."""
    self.state = ActionState.FAILED
    self.message = message
    self.finished = time.time()



########################################################################
#                               MESSAGES                               #
########################################################################
class ActionStarted(Message):
  """An action began executing on the lane."""

  def __init__(self, action: Action) -> None:
    super().__init__()
    self.action = action


class ActionFinished(Message):
  """An action finished on the lane; carries its ``Result``."""

  def __init__(self, action: Action, result: Result) -> None:
    super().__init__()
    self.action = action
    self.result = result



########################################################################
#                             ACTION LANE                              #
########################################################################
class ActionLane:
  """One serial worker thread feeding ``Commands.run``."""

  def __init__(self, app, commands, settings):
    self._app = app
    self._commands = commands
    self._settings = settings
    self._queue: "queue.SimpleQueue[Optional[Action]]" = queue.SimpleQueue()
    self._thread: Optional[threading.Thread] = None

  def start(self) -> None:
    self._thread = threading.Thread(
      target=self._loop, name="action-lane", daemon=True,
    )
    self._thread.start()

  def stop(self) -> None:
    self._queue.put(None)
    if self._thread is not None:
      self._thread.join(timeout=2.0)
      self._thread = None

  def submit(self, action: Action) -> None:
    self._queue.put(action)

  def _loop(self) -> None:
    while True:
      action = self._queue.get()
      if action is None:
        return
      action.start()
      self._app.post_message(ActionStarted(action))
      try:
        result = self._commands.run(
          list(action.tokens),
          getattr(self._settings, "active_conversation", None),
        )
      except Exception as e:  # a crash here would kill the lane
        logger.error(f"Action '{action.line}' crashed: {e}", exc_info=True)
        result = Result(success=False, message=f"Command crashed: {e}")
      action.finish(result)
      self._app.post_message(ActionFinished(action, result))
