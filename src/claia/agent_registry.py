"""
Agent registry for the CLAIA agents system.

This module provides an AgentRegistry that manages agent plugins and processes requests.
"""

import logging
import threading
import time
from typing import Any, Optional, Dict

# Internal dependencies
from claia.lib.results import Result
from claia.lib.process import Process
from claia.lib.queue import ProcessQueue
from claia.manager import UnifiedManager
from claia.models_registry import ModelRegistry
from claia.lib.enums.agent import ProcessStatus



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                            AGENT REGISTRY                            #
########################################################################
class AgentRegistry:
  """
  Manages agents in the CLAIA application.

  This registry loads agent plugins and dispatches process requests to the
  appropriate agent implementation based on the process's agent_type.
  """

  def __init__(self, model_registry=None, process_queue=None):
    """Initialize the AgentRegistry.

    Args:
        model_registry: ModelRegistry instance to inject into agents (optional)
        process_queue: ProcessQueue instance to use for process management (optional)
    """
    logger.debug("Initializing Agent Registry")

    # Initialize agent manager
    self.manager = UnifiedManager()

    # Initialize model registry
    self.model_registry = model_registry or ModelRegistry()

    # Initialize process queue
    self.process_queue = process_queue or ProcessQueue()

    # Worker management
    self._workers = []  # List of worker threads
    self._shutdown = threading.Event()  # Signal for workers to stop

    # Load all plugins
    self.manager.load_all_plugins()

    logger.info("AgentRegistry initialized successfully")

  def process(self, process: Process) -> Process:
    """
    Process the given process by dispatching to the appropriate agent implementation.

    Args:
        process: The process to be executed

    Returns:
        The updated process with results or error information
    """
    try:
      logger.debug(f"Processing {process.id} with agent type '{process.agent_type}'")

      # Get the agent class for this agent type
      agent_class = self.manager.get_agent_class(process.agent_type)

      if not agent_class:
        error_msg = f"No agent found for type '{process.agent_type}'"
        logger.error(error_msg)
        process.mark_failed(error_msg)
        return process

      # Process using the agent class, injecting model registry and all parameters as kwargs
      logger.debug(f"Using agent class {agent_class.__name__} for {process.id}")
      result = agent_class.process(process, model_registry=self.model_registry, **process.parameters)

      return result

    except Exception as e:
      logger.error(f"Error processing {process.id}: {str(e)}")
      process.mark_failed(f"Registry error: {str(e)}")
      return process

  def get_agent_class(self, agent_name: str) -> Optional[type]:
    """
    Get the agent class for a specific agent name.

    Args:
        agent_name: The name of the agent to get the class for

    Returns:
        The agent class that can handle the specified agent type, or None if not found
    """
    return self.manager.get_agent_class(agent_name)

  def add_process(self, process: Process) -> str:
    """
    Add a process to the queue for execution.

    Args:
        process: The process to add to the queue

    Returns:
        The ID of the process
    """
    return self.process_queue.put(process)

  def process_next(self, block=False, timeout=None) -> Optional[Process]:
    """
    Get and process the next process from the queue.

    Args:
        block: Whether to block until a process is available
        timeout: How long to wait for a process to become available

    Returns:
        The processed Process object or None if no process was available
    """
    process = self.process_queue.get(block=block, timeout=timeout)
    if process:
      # Skip cancelled processes
      if process.status == ProcessStatus.CANCELLED:
        return None

      # Process using the agent registry
      processed = self.process(process)
      self.process_queue.update(processed)
      return processed
    return None

  def process_by_id(self, process_id: str) -> Optional[Process]:
    """
    Process a specific process identified by its ID.

    Args:
        process_id: The ID of the process to process

    Returns:
        The processed Process object or None if the process wasn't found
        or wasn't in a PENDING state
    """
    process = self.process_queue.get_by_id(process_id)
    if process and process.status == ProcessStatus.PENDING:
      processed = self.process(process)
      self.process_queue.update(processed)
      return processed
    return None

  def _worker_loop(self):
    """Worker thread function that processes items from the queue."""
    while not self._shutdown.is_set():
      try:
        # Get and process a single item
        self.process_next(block=True, timeout=1.0)
      except Exception as e:
        logger.exception(f"Error in worker thread: {e}")
        # Continue processing even if one item fails
        continue

    logger.debug("Worker thread shutting down")

  def start_workers(self, num_workers: int = 1):
    """
    Start worker threads that process items from the queue.

    Args:
        num_workers: Number of worker threads to start
    """
    logger.info(f"Starting {num_workers} worker threads")
    self._shutdown.clear()

    for i in range(num_workers):
      worker = threading.Thread(target=self._worker_loop, daemon=True, name=f"AgentRegistry-Worker-{i+1}")
      worker.start()
      self._workers.append(worker)

    logger.debug(f"Started {num_workers} workers, total active: {len(self._workers)}")

  def stop_workers(self, wait: bool = True, timeout: float = 5.0):
    """
    Stop all worker threads.

    Args:
        wait: Whether to wait for workers to stop
        timeout: How long to wait for workers to stop
    """
    logger.info("Stopping worker threads")
    self._shutdown.set()

    if wait:
      workers = list(self._workers)

      for worker in workers:
        worker.join(timeout=timeout / len(workers) if workers else timeout)

      # Clean up worker list
      self._workers = [w for w in self._workers if w.is_alive()]
      if self._workers:
        logger.warning(f"{len(self._workers)} workers still running after timeout")
      else:
        logger.debug("All workers stopped successfully")

  def set_worker_count(self, count: int):
    """
    Set the number of worker threads for the AgentRegistry.

    If the AgentRegistry already has workers, they will be stopped and
    new workers started with the updated count.

    Args:
        count: Number of worker threads to use
    """
    # Ensure at least one worker
    worker_count = max(1, count)

    # Stop existing workers if any
    self.stop_workers(wait=True, timeout=120.0)

    # Start new workers with updated count
    self.start_workers(worker_count)
    logger.debug(f"Updated AgentRegistry to use {worker_count} worker(s)")
