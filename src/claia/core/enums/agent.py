# External dependencies
from enum import Enum


########################################################################
#                                ENUMS                                 #
########################################################################
class AgentStatus(Enum):
  """
  A step's report of what happened.

  Returned by ``BaseAgent.step`` implementations. The framework
  converts it into the task's status transition: ``CONTINUE`` leaves
  the task runnable (the queue re-enqueues it); the rest are terminal.
  """
  CONTINUE = "continue"
  COMPLETED = "completed"
  FAILED = "failed"
  CANCELLED = "cancelled"
