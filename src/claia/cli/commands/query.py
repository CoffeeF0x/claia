"""
Query command: the one-shot task-wiring path.

Builds the task from the active settings, mirrors the agent's tag
segmentation through a ``StreamRouter``, and renders block events
with a ``BlockRenderer``. This is the only place the CLI wires a
task's callbacks to terminal output.
"""

import logging
import threading
from typing import Any, List, Optional

from ...core.enums.task import TaskEvent, TaskStatus
from ...core.results import Result
from ...framework.task import Task
from ..renderer import BlockRenderer
from ..storage import JsonStore
from ..stream import StreamRouter
from ..utils import prepare_query_task, stream_tag_specs
from .base import BaseCommand


logger = logging.getLogger(__name__)


class QueryCommand(BaseCommand):
  """Command to send a one-shot query to the AI."""

  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """Send a message and stream the response to the terminal."""
    if not args:
      return Result(success=False, message=f"Missing query text. Usage: {self.format_command('query <your question>')}")

    query_text = ' '.join(args)

    try:
      task = prepare_query_task(self.settings, query_text)
      renderer = BlockRenderer(verbose=bool(getattr(self.settings, "verbose", False)))
      error = self._run_task(task, renderer)

      if error is not None:
        # The renderer already put the error on stderr; a bare
        # failure result keeps the exit code non-zero without
        # printing it twice.
        return Result(success=False)
      return Result(success=True)

    except Exception as e:
      self.logger.error(f"Error processing query: {e}", exc_info=True)
      return Result(success=False, message=f"Error processing query: {str(e)}")

  def _run_task(self, task: Task, renderer: BlockRenderer) -> Optional[str]:
    """Submit ``task`` and stream its output through router + renderer.

    Blocks until the task is terminal. Returns the error message on
    failure, ``None`` otherwise.
    """
    router = StreamRouter(stream_tag_specs(self.registry, task.parameters.get("model_id")))
    store = JsonStore(self.settings.files_directory)
    done = threading.Event()
    error_holder: List[Optional[str]] = [None]

    def persist():
      # Save only when domain events indicate mutations; by now the
      # conversation already reflects every tool result and utility.
      if task.conversation.pull_events():
        if not store.save(task.conversation):
          logger.error("Failed to save conversation")

    def on_chunk(chunk):
      renderer.handle_all(router.feed(chunk))

    def on_artifact(artifact, message_id):
      if store.save(artifact):
        renderer.handle_all(router.feed_artifact(artifact))
      else:
        logger.error(f"Failed to save artifact for message {message_id}")

    # Terminal callbacks must always release the wait, even when the
    # render sink is gone (e.g. stdout closed by a downstream pipe).
    def on_complete(_result):
      try:
        renderer.handle_all(router.end(TaskStatus.COMPLETED))
        persist()
      finally:
        done.set()

    def on_error(error_msg):
      error_holder[0] = str(error_msg)
      try:
        renderer.handle_all(router.end(TaskStatus.FAILED, error=str(error_msg)))
      finally:
        done.set()

    def on_cancelled(_result=None):
      try:
        renderer.handle_all(router.end(TaskStatus.CANCELLED))
        persist()
      finally:
        done.set()

    task.on(TaskEvent.CHUNK, on_chunk)
    task.on(TaskEvent.ARTIFACT, on_artifact)
    task.on(TaskEvent.COMPLETE, on_complete)
    task.on(TaskEvent.ERROR, on_error)
    task.on(TaskEvent.CANCELLED, on_cancelled)

    self.registry.add_task(task)
    done.wait()
    return error_holder[0]
