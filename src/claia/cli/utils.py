"""
Utility functions for the CLAIA CLI.
"""

import threading
import logging
from typing import Optional

from ..framework.process import Process
from ..core.enums.process import ProcessEvent
from .storage import JsonStore


logger = logging.getLogger(__name__)


def wait_for_process(
    process: Process,
    store: Optional[JsonStore] = None,
    save_conversation: bool = True,
    timeout: Optional[float] = None
) -> bool:
  """
  Block until a process completes, using the callback-based event system.

  Before calling this, register TOKEN, COMPLETE, and ERROR callbacks
  on the process. This helper simply waits for the done event to be set
  by one of those callbacks.
  """
  done = threading.Event()
  success_flag = [True]

  def on_complete(*args):
    if save_conversation and store and process.conversation:
      if not store.save(process.conversation):
        logger.error("Failed to save conversation")
    done.set()

  def on_error(error_msg):
    success_flag[0] = False
    done.set()

  process.on(ProcessEvent.COMPLETE, on_complete)
  process.on(ProcessEvent.ERROR, on_error)

  done.wait(timeout=timeout)
  return success_flag[0]
