"""
This module contains the Process class for CLAIA agent system.
A Process represents a unit of work to be executed by an agent.
"""

# External dependencies
import uuid, time, logging, threading
from typing import Optional, Dict, Any, Callable, List

# Internal dependencies
from claia.core.enums.process import ProcessStatus
from claia.core.data import Conversation


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
    # Cooperative cancellation. Hosts running an agent on a worker thread
    # can call request_cancel() to ask the agent to stop at the next
    # safe point. Long-running agents should poll cancel_requested
    # between unit-of-work steps (e.g. between streamed tokens) and
    # break cleanly. Implemented via threading.Event so it is safe to
    # set from a different thread than the one running the agent.
    self.cancel_event: threading.Event = threading.Event()

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

  # ── Cancellation ──────────────────────────────────────────────────

  @property
  def cancel_requested(self) -> bool:
    """True once a host has called :meth:`request_cancel`."""
    return self.cancel_event.is_set()

  def request_cancel(self) -> None:
    """
    Request cooperative cancellation of the running agent.

    Setting the event does not preempt the agent; the agent must
    poll :attr:`cancel_requested` and break out of its work loop.
    Safe to call from any thread.
    """
    self.cancel_event.set()

  def to_dict(self, parameter_value_max_len: int = 160) -> Dict[str, Any]:
    """JSON-friendly summary for monitoring (queue snapshots, admin APIs)."""
    status = self.status
    status_val = status.value if isinstance(status, ProcessStatus) else str(status)
    params: Dict[str, str] = {}
    for key, val in (self.parameters or {}).items():
      text = repr(val)
      if len(text) > parameter_value_max_len:
        text = text[:parameter_value_max_len] + "…"
      params[str(key)] = text
    return {
      "id": self.id,
      "agent_type": self.agent_type,
      "status": status_val,
      "parent_id": self.parent_id,
      "created_at": self.created_at,
      "started_at": self.started_at,
      "completed_at": self.completed_at,
      "error": self.error,
      "cancel_requested": self.cancel_requested,
      "parameters": params,
    }
