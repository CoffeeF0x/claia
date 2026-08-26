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

from ...core.enums.conversation import MessageRole
from ...core.enums.model import SourcePreference
from ...core.enums.task import TaskEvent, TaskStatus
from ...core.parser import resolve_tag_specs
from ...core.results import Result
from ...framework.task import Task
from ..renderer import BlockRenderer
from ..storage import JsonStore
from ..stream import StreamRouter
from ..utils import active_system, ensure_active_conversation
from .base import BaseCommand


logger = logging.getLogger(__name__)
DEFAULT_AGENT = "simple"


class QueryCommand(BaseCommand):
  """Command to send a one-shot query to the AI."""

  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """Send a message and stream the response to the terminal."""
    if not args:
      return Result(success=False, message=f"Missing query text. Usage: {self.format_command('query <your question>')}")

    query_text = ' '.join(args)

    try:
      conversation = ensure_active_conversation(self.settings)

      if not self.settings.active_agent:
        self.settings.active_agent = self.settings.default_agent or DEFAULT_AGENT

      conversation.add_message(MessageRole.USER, query_text)

      task = self._build_task(conversation)
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

  def _build_task(self, conversation: Any) -> Task:
    """Assemble the task from the active settings."""
    parameters = {
      "source_preference": SourcePreference.ANY,
      "model_id": self.settings.active_model,
      **self.settings.get_user_kwargs(),
    }
    system = active_system(self.settings)
    if system:
      parameters["system"] = system

    return Task(
      agent_type=self.settings.active_agent,
      conversation=conversation,
      parameters=parameters,
    )

  def _run_task(self, task: Task, renderer: BlockRenderer) -> Optional[str]:
    """Submit ``task`` and stream its output through router + renderer.

    Blocks until the task is terminal. Returns the error message on
    failure, ``None`` otherwise.
    """
    router = StreamRouter(self._tag_specs(task.parameters.get("model_id")))
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

  def _tag_specs(self, model_id: Optional[str]):
    """Mirror the agent's spec resolution: exact id, else defaults."""
    definitions = self.registry.get_supported_models()
    model_def = None
    if isinstance(definitions, dict) and model_id in definitions:
      model_def = definitions[model_id]
    return resolve_tag_specs(model_def)
