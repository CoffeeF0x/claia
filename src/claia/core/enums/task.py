# External dependencies
from enum import Enum


########################################################################
#                                ENUMS                                 #
########################################################################
class TaskStatus(Enum):
  """Status of a task."""
  PENDING = "pending"
  PROCESSING = "processing"
  COMPLETED = "completed"
  FAILED = "failed"
  CANCELLED = "cancelled"


class TaskEvent(Enum):
  """Callback names on ``Task.on`` / ``Task.emit``.

  Job lifecycle and live output. Conversation mutations
  (including stream start/end) are ``EventType`` on the
  conversation, not task events.
  """
  CHUNK = "chunk"
  ARTIFACT = "artifact"
  COMPLETE = "complete"
  ERROR = "error"
  CANCELLED = "cancelled"
