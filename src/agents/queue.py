"""
This module contains the ProcessQueue class for CLAIA agent system.
The ProcessQueue manages processes that need to be executed by agents.
"""

# External dependencies
import queue, threading, time, logging
from typing import Optional, List, Dict

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

  This class is implemented as a singleton to ensure only one instance
  exists throughout the application.
  """
  # Class variables for singleton pattern
  _instance = None
  _worker_count = 1  # Default number of workers
  _init_lock = threading.Lock()

  def __new__(cls, *args, **kwargs):
    """Override __new__ to implement the singleton pattern."""
    with cls._init_lock:
      if cls._instance is None:
        logger = logging.getLogger(__name__)
        logger.debug("Creating singleton ProcessQueue instance")
        cls._instance = super(ProcessQueue, cls).__new__(cls)
        # Mark as uninitialized so we know to call init
        cls._instance._initialized = False
      return cls._instance

  def __init__(self):
    """Initialize the ProcessQueue singleton instance."""
    # Only initialize once
    if getattr(self, '_initialized', False):
      return

    self._queue = queue.Queue()
    self._lock = threading.Lock()
    self._processes = {}  # id -> Process mapping for quick lookups
    self._workers = []  # List of worker threads
    self._shutdown = threading.Event()  # Signal for workers to stop
    self._logger = logging.getLogger(__name__)
    self._initialized = True

    # Start the default number of workers
    self.start_workers(self._worker_count)

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
        return process

    # Process the request directly with the Agent class
    updated_process = Agent.process(process)

    # Update the process in the queue
    self.update(updated_process)

    return updated_process

  def _worker_loop(self):
    """Worker thread function that processes items from the queue."""
    self._logger.debug("Worker thread started")
    while not self._shutdown.is_set():
      try:
        # Get next process from queue with a timeout to check shutdown flag periodically
        process = self.get(block=True, timeout=1.0)
        if process and process.status == ProcessStatus.PENDING:
          # Process the request
          self._logger.debug(f"Worker processing: {process.id}")
          updated_process = Agent.process(process)
          self.update(updated_process)
      except Exception as e:
        self._logger.error(f"Error in worker thread: {str(e)}")

      # Small delay to prevent CPU spinning
      time.sleep(0.01)

    self._logger.debug("Worker thread stopped")

  def start_workers(self, num_workers: int = 1):
    """
    Start worker threads that process items from the queue.

    Args:
        num_workers: Number of worker threads to start
    """
    self._logger.info(f"Starting {num_workers} worker threads")
    self._shutdown.clear()

    with self._lock:
      # Clean up any terminated workers
      self._workers = [w for w in self._workers if w.is_alive()]

      # Start new workers
      for _ in range(num_workers):
        worker = threading.Thread(target=self._worker_loop)
        worker.daemon = True  # Make thread exit when main thread exits
        worker.start()
        self._workers.append(worker)

    self._logger.debug(f"Started {num_workers} workers, total active: {len(self._workers)}")

  def stop_workers(self, wait: bool = True, timeout: float = 5.0):
    """
    Stop all worker threads.

    Args:
        wait: Whether to wait for workers to stop
        timeout: How long to wait for workers to stop
    """
    self._logger.info("Stopping worker threads")
    self._shutdown.set()

    if wait:
      with self._lock:
        workers = list(self._workers)

      for worker in workers:
        worker.join(timeout=timeout / len(workers))

      with self._lock:
        # Clean up worker list
        self._workers = [w for w in self._workers if w.is_alive()]
        if self._workers:
          self._logger.warning(f"{len(self._workers)} workers still running after timeout")
        else:
          self._logger.debug("All workers stopped successfully")

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

  def set_worker_count(self, count: int):
    """
    Set the number of worker threads for the ProcessQueue singleton.

    If the ProcessQueue already has workers, they will be stopped and
    new workers started with the updated count.

    Args:
        count: Number of worker threads to use
    """
    # Ensure at least one worker
    worker_count = max(1, count)

    # Update the class variable for future instances
    ProcessQueue._worker_count = worker_count

    # If already initialized, update workers
    if hasattr(self, '_initialized') and self._initialized:
      # Stop existing workers if any
      self.stop_workers(wait=True, timeout=120.0)
      # Start new workers with updated count
      self.start_workers(worker_count)
      self._logger.debug(f"Updated ProcessQueue to use {worker_count} worker(s)")
    else:
      # Set worker count for initialization
      self._worker_count = worker_count