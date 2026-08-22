"""
This module contains the TaskQueue class for CLAIA agent system.
The TaskQueue manages tasks that need to be executed by agents.
"""

# External dependencies
import queue, time, logging, threading
from typing import Any, Callable, DefaultDict, Dict, List, Optional

# Internal dependencies
from .task import Task
from ..core.enums.task import TaskStatus
from ..core.enums.task_queue import TaskQueueHook


########################################################################
#                            TASK QUEUE                                #
########################################################################
class TaskQueue:
  """
  A thread-safe queue for tasks.

  This queue is used to manage tasks that need to be executed by agents.
  """
  def __init__(self):
    """Initialize the TaskQueue."""
    self._queue = queue.Queue()
    self._lock = threading.Lock()
    self._tasks = {}  # id -> Task mapping for quick lookups
    self._logger = logging.getLogger(__name__)
    self._hooks: DefaultDict[TaskQueueHook, List[Callable[..., Any]]] = DefaultDict(list)

  def put(self, task: Task):
    """
    Add a task to the queue.

    Args:
        task: The task to add to the queue

    Returns:
        The ID of the task
    """
    with self._lock:
      # Store in our lookup dictionary
      self._tasks[task.id] = task

      # Add to queue
      self._queue.put(task.id)

    self._emit_hook(TaskQueueHook.ENQUEUE, task=task)
    return task.id

  def get(self, block=True, timeout=None) -> Optional[Task]:
    """
    Get the next task from the queue.

    Args:
        block: Whether to block until a task is available
        timeout: How long to wait for a task to become available

    Returns:
        The next task from the queue, or None if no task is available
    """
    try:
      task_id = self._queue.get(block=block, timeout=timeout)
      dequeued = None
      with self._lock:
        task = self._tasks.get(task_id)
        if task:
          # Only remove from tasks dict if status is COMPLETED, FAILED, or CANCELLED
          if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            self._tasks.pop(task_id, None)
          dequeued = task
      if dequeued is not None:
        self._emit_hook(TaskQueueHook.DEQUEUE, task=dequeued)
      return dequeued
    except queue.Empty:
      return None

  def get_by_id(self, task_id: str) -> Optional[Task]:
    """
    Get a task by its ID without removing it from the queue.

    Args:
        task_id: The ID of the task to get

    Returns:
        The task with the given ID, or None if no such task exists
    """
    with self._lock:
      return self._tasks.get(task_id)

  def update(self, task: Task):
    """
    Update a task in the queue.

    Args:
        task: The task to update
    """
    with self._lock:
      self._tasks[task.id] = task

    self._emit_hook(TaskQueueHook.UPDATE, task=task)

  def remove(self, task_id: str) -> bool:
    """
    Remove a task from the queue.

    Note: This doesn't remove from the queue directly
    (which is not easily possible), but marks it as cancelled
    so it will be ignored when retrieved.

    Args:
        task_id: The ID of the task to remove

    Returns:
        True if the task was found and cancelled, False otherwise
    """
    removed_task = None
    with self._lock:
      task = self._tasks.get(task_id)
      if task:
        task.mark_cancelled()
        removed_task = task
    if removed_task is not None:
      self._emit_hook(TaskQueueHook.REMOVE, task=removed_task)
      return True
    return False

  def snapshot(self) -> List[Dict[str, Any]]:
    """
    Return a point-in-time list of tracked tasks for observability.

    Entries include tasks still awaiting work, actively running, and any
    terminal records retained in the lookup table.
    """
    with self._lock:
      rows = [t.to_dict() for t in self._tasks.values()]
    rows.sort(key=lambda r: (r.get("created_at") or 0, r.get("id") or ""))
    return rows

  def size(self) -> int:
    """
    Get the number of tasks in the queue.

    Returns:
        The number of tasks in the queue
    """
    return self._queue.qsize()

  def wait_for_task(self, task_id: str, timeout: float = None, check_interval: float = 0.1) -> Optional[Task]:
    """
    Wait for a specific task to complete.

    Args:
        task_id: The ID of the task to wait for
        timeout: Maximum time to wait in seconds (None for no timeout)
        check_interval: How often to check the task status in seconds

    Returns:
        The completed Task object or None if timed out or not found
    """
    start_time = time.time()
    self._logger.debug(f"Waiting for task: {task_id}")

    while timeout is None or time.time() - start_time < timeout:
      task = self.get_by_id(task_id)
      if not task:
        self._logger.debug(f"Task {task_id} not found in queue")
        return None

      if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
        self._logger.debug(f"Task {task_id} completed with status: {task.status}")
        return task

      time.sleep(check_interval)

    self._logger.warning(f"Timed out waiting for task {task_id} after {timeout} seconds")
    return self.get_by_id(task_id)

  def wait_for_all_tasks(self, timeout: float = None, check_interval: float = 0.1) -> bool:
    """
    Wait for all tasks in the queue to complete.

    Args:
        timeout: Maximum time to wait in seconds (None for no timeout)
        check_interval: How often to check the queue status in seconds

    Returns:
        True if all tasks completed, False if timed out
    """
    start_time = time.time()
    self._logger.debug("Waiting for all tasks to complete")

    while timeout is None or time.time() - start_time < timeout:
      with self._lock:
        # Get all task IDs that are still pending
        pending_tasks = [tid for tid, item in self._tasks.items()
                         if item.status == TaskStatus.PENDING]

      if not pending_tasks:
        self._logger.debug("All tasks completed successfully")
        return True

      self._logger.debug(f"Still waiting for {len(pending_tasks)} tasks")
      time.sleep(check_interval)

    self._logger.warning(f"Timed out waiting for all tasks after {timeout} seconds")
    return False

  ######################################################################
  #                               HOOKS                                #
  ######################################################################
  def add_hook(self, hook: TaskQueueHook, callback: Callable[..., Any]) -> None:
    """Register a native callback for a queue lifecycle event (thread-safe)."""
    with self._lock:
      self._hooks[hook].append(callback)

  def remove_hook(self, hook: TaskQueueHook, callback: Callable[..., Any]) -> None:
    """Unregister a callback previously passed to :meth:`add_hook`."""
    with self._lock:
      cbs = self._hooks.get(hook)
      if not cbs:
        return
      try:
        cbs.remove(callback)
      except ValueError:
        pass

  def _emit_hook(self, hook: TaskQueueHook, **payload: Any) -> None:
    with self._lock:
      callbacks = list(self._hooks.get(hook, ()))
    for cb in callbacks:
      try:
        cb(**payload)
      except Exception as e:
        self._logger.error("Queue hook %r failed: %s", hook, e)
