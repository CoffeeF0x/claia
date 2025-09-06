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
