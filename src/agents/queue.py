"""
This module contains the ProcessQueue class for CLAIA agent system.
The ProcessQueue manages processes that need to be executed by agents.
"""

# External dependencies
import queue, threading
from typing import Optional

# Internal dependencies
from .process import Process
from .agent import Agent
from enums import ProcessStatus



########################################################################
#                           PROCESS QUEUE                              #
########################################################################
class ProcessQueue:
  """
  A thread-safe queue for processes.

  This queue is used to manage processes that need to be executed by agents.
  Processes are processed in FIFO (First In, First Out) order.
  """
  def __init__(self):
    """Initialize a new ProcessQueue."""
    self._queue = queue.Queue()
    self._lock = threading.Lock()
    self._processes = {}  # id -> Process mapping for quick lookups

  def put(self, process: Process):
    """
    Add a process to the queue.

    Args:
        process: The process to add to the queue

    Returns:
        The ID of the process
    """
    with self._lock:
      # Store in our lookup dictionary
      self._processes[process.id] = process

      # Add to queue
      self._queue.put(process.id)

    return process.id

  def get(self, block=True, timeout=None) -> Optional[Process]:
    """
    Get the next process from the queue.

    Args:
        block: Whether to block until a process is available
        timeout: How long to wait for a process to become available

    Returns:
        The next process from the queue, or None if no process is available
    """
    try:
      process_id = self._queue.get(block=block, timeout=timeout)
      with self._lock:
        process = self._processes.get(process_id)
        if process:
          # Only remove from processes dict if status is COMPLETED, FAILED, or CANCELLED
          if process.status in [ProcessStatus.COMPLETED, ProcessStatus.FAILED, ProcessStatus.CANCELLED]:
            self._processes.pop(process_id, None)
          return process
        return None
    except queue.Empty:
      return None

  def get_by_id(self, process_id: str) -> Optional[Process]:
    """
    Get a process by its ID without removing it from the queue.

    Args:
        process_id: The ID of the process to get

    Returns:
        The process with the given ID, or None if no such process exists
    """
    with self._lock:
      return self._processes.get(process_id)

  def update(self, process: Process):
    """
    Update a process in the queue.

    Args:
        process: The process to update
    """
    with self._lock:
      self._processes[process.id] = process

  def remove(self, process_id: str) -> bool:
    """
    Remove a process from the queue.

    Note: This doesn't remove from the queue directly
    (which is not easily possible), but marks it as cancelled
    so it will be ignored when retrieved.

    Args:
        process_id: The ID of the process to remove

    Returns:
        True if the process was found and cancelled, False otherwise
    """
    with self._lock:
      process = self._processes.get(process_id)
      if process:
        process.mark_cancelled()
        return True
      return False

  def size(self) -> int:
    """
    Get the number of processes in the queue.

    Returns:
        The number of processes in the queue
    """
    with self._lock:
      return len(self._processes)

  def process(self, block=False, timeout=None) -> Optional[Process]:
    """
    Get a process from the queue and process it using the Agent class.

    Args:
        block: Whether to block until a process is available
        timeout: How long to wait for a process to become available

    Returns:
        The processed Process object or None if no process was available
    """
    # Get the next process from the queue
    process = self.get(block=block, timeout=timeout)
    if not process or process.status != ProcessStatus.PENDING:
      return None

    # Process the request directly with the Agent class
    updated_process = Agent.process(process)

    # Update the process in the queue
    self.update(updated_process)

    return updated_process

  def process_by_id(self, process_id: str) -> Optional[Process]:
    """
    Process a specific process identified by its ID.

    Args:
        process_id: The ID of the process to process

    Returns:
        The processed Process object or None if the process wasn't found
        or wasn't in a PENDING state
    """
    with self._lock:
      process = self._processes.get(process_id)
      if not process or process.status != ProcessStatus.PENDING:
        return None

    # Process the request directly with the Agent class
    updated_process = Agent.process(process)

    # Update the process in the queue
    self.update(updated_process)

    return updated_process