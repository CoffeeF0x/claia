# External dependencies
from enum import Enum


class ProcessQueueHook(str, Enum):
  """Lifecycle events for :class:`claia.framework.queue.ProcessQueue` native hooks."""

  ENQUEUE = "enqueue"
  DEQUEUE = "dequeue"
  UPDATE = "update"
  REMOVE = "remove"
