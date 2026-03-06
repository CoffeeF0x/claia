"""
Utility functions for the CLAIA CLI.

This module contains reusable utility functions for common CLI operations.
"""

import threading
import logging
from typing import Optional

from claia.lib.process import Process
from claia.lib.data import FileSystemRepository


logger = logging.getLogger(__name__)


def wait_for_process(
    process: Process,
    file_repo: Optional[FileSystemRepository] = None,
    save_conversation: bool = True,
    timeout: Optional[float] = None
) -> bool:
  """
  Block until a process completes, using the callback-based event system.

  Before calling this, register "token", "complete", and "error" callbacks
  on the process. This helper simply waits for the done event to be set
  by one of those callbacks.

  Args:
      process: The Process object to wait on (must have callbacks registered)
      file_repo: Optional FileSystemRepository for saving conversations
      save_conversation: Whether to save the conversation after completion
      timeout: Optional timeout in seconds

  Returns:
      bool: True if process completed successfully, False otherwise
  """
  done = threading.Event()
  success_flag = [True]

  original_complete = None
  original_error = None

  def on_complete(*args):
    if save_conversation and file_repo and process.conversation:
      if not file_repo.save(process.conversation):
        logger.error("Failed to save conversation")
    done.set()

  def on_error(error_msg):
    success_flag[0] = False
    done.set()

  process.on("complete", on_complete)
  process.on("error", on_error)

  done.wait(timeout=timeout)
  return success_flag[0]
