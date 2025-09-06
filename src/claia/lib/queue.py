"""
This module contains the ProcessQueue class for CLAIA agent system.
The ProcessQueue manages processes that need to be executed by agents.
"""

# External dependencies
import queue, time, logging, threading
from typing import Optional

# Internal dependencies
from .process import Process
from claia.lib.enums.process import ProcessStatus



########################################################################
#                           PROCESS QUEUE                              #
########################################################################
class ProcessQueue:
  """
  A thread-safe queue for processes.

  This queue is used to manage processes that need to be executed by agents.
  """
  def __init__(self):
    """Initialize the ProcessQueue."""
    self._queue = queue.Queue()
    self._lock = threading.Lock()
    self._processes = {}  # id -> Process mapping for quick lookups
    self._logger = logging.getLogger(__name__)

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
    return self._queue.qsize()



  def wait_for_process(self, process_id: str, timeout: float = None, check_interval: float = 0.1) -> Optional[Process]:
    """
    Wait for a specific process to complete.

    Args:
        process_id: The ID of the process to wait for
        timeout: Maximum time to wait in seconds (None for no timeout)
        check_interval: How often to check the process status in seconds

    Returns:
        The completed Process object or None if timed out or not found
    """
    start_time = time.time()
    self._logger.debug(f"Waiting for process: {process_id}")

    while timeout is None or time.time() - start_time < timeout:
      process = self.get_by_id(process_id)
      if not process:
        self._logger.debug(f"Process {process_id} not found in queue")
        return None

      if process.status in [ProcessStatus.COMPLETED, ProcessStatus.FAILED, ProcessStatus.CANCELLED]:
        self._logger.debug(f"Process {process_id} completed with status: {process.status}")
        return process

      time.sleep(check_interval)

    self._logger.warning(f"Timed out waiting for process {process_id} after {timeout} seconds")
    return self.get_by_id(process_id)

  def wait_for_all_processes(self, timeout: float = None, check_interval: float = 0.1) -> bool:
    """
    Wait for all processes in the queue to complete.

    Args:
        timeout: Maximum time to wait in seconds (None for no timeout)
        check_interval: How often to check the queue status in seconds

    Returns:
        True if all processes completed, False if timed out
    """
    start_time = time.time()
    self._logger.debug("Waiting for all processes to complete")

    while timeout is None or time.time() - start_time < timeout:
      with self._lock:
        # Get all process IDs that are still pending
        pending_processes = [pid for pid, proc in self._processes.items()
                           if proc.status == ProcessStatus.PENDING]

      if not pending_processes:
        self._logger.debug("All processes completed successfully")
        return True

      self._logger.debug(f"Still waiting for {len(pending_processes)} processes")
      time.sleep(check_interval)

    self._logger.warning(f"Timed out waiting for all processes after {timeout} seconds")
    return False




