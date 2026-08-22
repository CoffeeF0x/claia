# External dependencies
from enum import Enum


########################################################################
#                                ENUMS                                 #
########################################################################
class ProcessStatus(Enum):
  """Status of a process."""
  PENDING = "pending"
  PROCESSING = "processing"
  COMPLETED = "completed"
  FAILED = "failed"
  CANCELLED = "cancelled"


class ProcessEvent(Enum):
  """Callback names on ``Process.on`` / ``Process.emit``.

  Job lifecycle and live output. Conversation mutations
  (including stream start/end) are ``EventType`` on the
  conversation, not process events.
  """
  START = "start"
  TOKEN = "token"
  CHUNK = "chunk"
  ARTIFACT = "artifact"
  COMPLETE = "complete"
  ERROR = "error"
  CANCELLED = "cancelled"
