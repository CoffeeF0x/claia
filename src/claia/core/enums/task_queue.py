# External dependencies
from enum import Enum


class TaskQueueHook(str, Enum):
  """Lifecycle events for :class:`claia.framework.queue.TaskQueue` native hooks."""

  ENQUEUE = "enqueue"
  DEQUEUE = "dequeue"
  UPDATE = "update"
  REMOVE = "remove"
