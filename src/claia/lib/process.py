"""
This module contains the Process class for CLAIA agent system.
A Process represents a unit of work to be executed by an agent.
"""

# External dependencies
import uuid, time
from typing import Optional, Dict, Any

# Internal dependencies
from claia.lib.enums.process import ProcessStatus
from claia.lib.data import Conversation



########################################################################
#                             PROCESS                                  #
########################################################################
class Process:
  """
  Represents a process to be executed by an agent.

  A process is a unit of work that can be executed by an agent.
  It contains all the information needed to execute the process,
  including the conversation context and any additional parameters.
  """
  def __init__(
    self,
    agent_type: str = "simple",
    conversation: Conversation = None,
    parameters: Dict[str, Any] = None,
    parent_id: Optional[str] = None,
    id: Optional[str] = None
  ):
    """
    Initialize a new Process.

    Args:
        agent_type: The type of agent that should handle this process
        conversation: The conversation object to use for this process
        parameters: Additional parameters for this process (should include model_id)
        parent_id: The ID of the parent process that created this process
        id: The ID of this process (generated if not provided)
    """
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

  def mark_started(self):
    """Mark the process as started."""
    self.status = ProcessStatus.PROCESSING
    self.started_at = time.time()

  def mark_completed(self, result: Any = None):
    """Mark the process as completed with an optional result."""
    self.status = ProcessStatus.COMPLETED
    self.result = result
    self.completed_at = time.time()

  def mark_failed(self, error: str):
    """Mark the process as failed with an error message."""
    self.status = ProcessStatus.FAILED
    self.error = error
    self.completed_at = time.time()

  def mark_cancelled(self):
    """Mark the process as cancelled."""
    self.status = ProcessStatus.CANCELLED
    self.completed_at = time.time()
