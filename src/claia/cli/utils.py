"""
Utility functions for the CLAIA CLI.
"""

import threading
import logging
from typing import Optional

from ..framework.task import Task
from ..core.data.models import Conversation
from ..core.enums.task import TaskEvent
from .storage import JsonStore


logger = logging.getLogger(__name__)


def active_system(settings) -> Optional[str]:
  """Return the CLI's active prompt text, or None if none is set."""
  prompt = getattr(settings, "active_prompt", None)
  content = getattr(prompt, "content", None) if prompt else None
  if isinstance(content, str) and content.strip():
    return content.strip()
  return None


def ensure_active_conversation(settings) -> Conversation:
  """Return the active conversation, creating one only when needed."""
  conversation = getattr(settings, "active_conversation", None)
  if conversation is None:
    conversation = Conversation()
    settings.active_conversation = conversation
  return conversation


def wait_for_task(
    task: Task,
    store: Optional[JsonStore] = None,
    save_conversation: bool = True,
    timeout: Optional[float] = None
) -> bool:
  """
  Block until a task completes, using the callback-based event system.

  Before calling this, register CHUNK, COMPLETE, and ERROR callbacks
  on the task. This helper simply waits for the done event to be set
  by one of those callbacks.
  """
  done = threading.Event()
  success_flag = [True]

  def on_complete(*args):
    if save_conversation and store and task.conversation:
      if not store.save(task.conversation):
        logger.error("Failed to save conversation")
    done.set()

  def on_error(error_msg):
    success_flag[0] = False
    done.set()

  task.on(TaskEvent.COMPLETE, on_complete)
  task.on(TaskEvent.ERROR, on_error)

  done.wait(timeout=timeout)
  return success_flag[0]
