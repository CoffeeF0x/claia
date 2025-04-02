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

  @classmethod
  def from_string(cls, agent_type_str: str) -> 'AgentType':
    """
    Convert a string to the corresponding AgentType enum value.

    Args:
        agent_type_str: The string representation of an agent type

    Returns:
        The matching AgentType enum value

    Raises:
        ValueError: If the string doesn't match any valid agent type
    """
    # First try matching by value (case-insensitive)
    for agent_type in cls:
      if agent_type.value.lower() == agent_type_str.lower():
        return agent_type

    # If that fails, try matching by name (case-insensitive)
    for agent_type in cls:
      if agent_type.name.lower() == agent_type_str.lower():
        return agent_type

    # If no match is found, raise an error
    valid_types = [f"{t.name} ({t.value})" for t in cls]
    raise ValueError(f"Invalid agent type: {agent_type_str}. Valid types are: {', '.join(valid_types)}")


class SourcePreference(Enum):
  """Enum for source preferences when deploying models."""
  ANY = "any"  # Use any available source
  API = "api"  # Prefer API sources
  LOCAL = "local"  # Prefer local deployment
  REMOTE = "remote"  # Prefer remote deployment