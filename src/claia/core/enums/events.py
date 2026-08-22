from enum import Enum, auto


class EventType(Enum):
  """All recognised domain event types."""
  CONVERSATION_CREATED = auto()
  MESSAGE_CREATED = auto()
  MESSAGE_UPDATED = auto()
  MESSAGE_DELETED = auto()
  MESSAGE_STREAM_START = auto()
  MESSAGE_STREAM_END = auto()
  ATTACHMENT_ADDED = auto()
  ATTACHMENT_REMOVED = auto()
  TITLE_CHANGED = auto()
