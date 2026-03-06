"""
This module contains the Process class for CLAIA agent system.
A Process represents a unit of work to be executed by an agent.
"""

# External dependencies
import uuid, time, logging
from typing import Optional, Dict, Any, Callable, List

# Internal dependencies
from claia.lib.enums.process import ProcessStatus
from claia.lib.data import Conversation


logger = logging.getLogger(__name__)



########################################################################
#                             PROCESS                                  #
########################################################################
class Process:
  """
  Represents a process to be executed by an agent.

  A process is a unit of work that can be executed by an agent.
  It contains all the information needed to execute the process,
  including the conversation context and any additional parameters.

  Supports an event callback system via on() and emit(). Consumers
  register callbacks before submitting the process to the queue.
  Agents emit events ("start", "token", "complete", "error") as they
  execute. Callbacks are fired from the worker thread — thread safety
  is the consumer's responsibility.
  """
  def __init__(
    self,
    agent_type: str = "simple",
    conversation: Conversation = None,
    parameters: Dict[str, Any] = None,
    parent_id: Optional[str] = None,
    id: Optional[str] = None
  ):
    self.id = id or str(uuid.uuid4())
    self.agent_type = agent_type
    self.status = ProcessStatus.PENDING
    self.parent_id = parent_id
    self.conversation = conversation
    self.parameters = parameters or {}
    self.result = None
    self.error = None
    self.created_at = time.time()
    self.started_at = None
    self.completed_at = None
    self._callbacks: Dict[str, List[Callable]] = {}

  # ── Callback API ──────────────────────────────────────────────────

  def on(self, event: str, callback: Callable) -> 'Process':
    """Register a callback for an event. Returns self for chaining."""
    self._callbacks.setdefault(event, []).append(callback)
    return self

  def emit(self, event: str, *args, **kwargs) -> None:
    """Fire all callbacks registered for *event*. Exceptions are logged, not raised."""
    for cb in self._callbacks.get(event, []):
      try:
        cb(*args, **kwargs)
      except Exception as e:
        logger.error(f"Callback error on '{event}' for process {self.id}: {e}")

  # ── State transitions ─────────────────────────────────────────────

  def mark_started(self):
    """Mark the process as started."""
    self.status = ProcessStatus.PROCESSING
    self.started_at = time.time()
    self.emit("start")

  def mark_completed(self, result: Any = None):
    """Mark the process as completed with an optional result."""
    self.status = ProcessStatus.COMPLETED
    self.result = result
    self.completed_at = time.time()
    self.emit("complete", result)

  def mark_failed(self, error: str):
    """Mark the process as failed with an error message."""
    self.status = ProcessStatus.FAILED
    self.error = error
    self.completed_at = time.time()
    self.emit("error", error)

  def mark_cancelled(self):
    """Mark the process as cancelled."""
    self.status = ProcessStatus.CANCELLED
    self.completed_at = time.time()
