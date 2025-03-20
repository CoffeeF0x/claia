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


class AgentType(Enum):
  """Types of agents that can handle processes."""
  SIMPLE = "simple"  # Simple agent that directly calls a model
  BOB = "bob"  # Bob agent that uses a specific system prompt


class SourcePreference(Enum):
  """Enum for source preferences when deploying models."""
  ANY = "any"  # Use any available source
  API = "api"  # Prefer API sources
  LOCAL = "local"  # Prefer local deployment
  REMOTE = "remote"  # Prefer remote deployment