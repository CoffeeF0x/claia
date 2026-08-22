"""
Query command for sending one-shot queries to the AI.
"""

import logging
import threading
from typing import List, Optional, Any

from ...core.results import Result
from ...core.enums.conversation import MessageRole
from ...core.enums.model import SourcePreference
from ...framework.task import Task
from ...core.enums.task import TaskEvent
from ..renderer import PacedRenderer
from ..storage import JsonStore
from ..utils import active_system, ensure_active_conversation
from .base import BaseCommand


logger = logging.getLogger(__name__)
DEFAULT_AGENT = "simple"


class QueryCommand(BaseCommand):
  """Command to send a one-shot query to the AI."""

  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """Send a message and get a response."""
    if not args:
      return Result(success=False, message=f"Missing query text. Usage: {self.format_command('query <your question>')}")

    query_text = ' '.join(args)

    try:
      conversation = ensure_active_conversation(self.settings)

      if not self.settings.active_agent:
        self.settings.active_agent = self.settings.default_agent or DEFAULT_AGENT

      conversation.add_message(MessageRole.USER, query_text)
      user_kwargs = self.settings.get_user_kwargs()

      done_event = threading.Event()
      error_holder = [None]

      parameters = {
        "source_preference": SourcePreference.ANY,
        "model_id": self.settings.active_model,
        **user_kwargs
      }
      system = active_system(self.settings)
      if system:
        parameters["system"] = system

      task = Task(
        agent_type=self.settings.active_agent,
        conversation=conversation,
        parameters=parameters
      )

      renderer = PacedRenderer()
      renderer.start()
      task.on(TaskEvent.TOKEN, renderer.feed)
      file_repo = JsonStore(self.settings.files_directory)
      saved_artifacts = []

      def on_artifact(artifact, message_id):
        if file_repo.save(artifact):
          saved_artifacts.append(artifact)
          logger.debug(f"Saved artifact {artifact.id} for message {message_id}")
        else:
          logger.error(f"Failed to save artifact for message {message_id}")

      def on_complete(full_response):
        renderer.finish(drain=True)
        if full_response and not full_response.endswith('\n'):
          print()
        for artifact in saved_artifacts:
          print(f"[Saved attachment: {artifact.name}]")
        if self.settings.active_conversation.pull_events():
          file_repo.save(self.settings.active_conversation)
        done_event.set()

      def on_error(error_msg):
        renderer.finish(drain=False)
        error_holder[0] = error_msg
        print(f"\nError: {error_msg}")
        done_event.set()

      def on_cancelled(_full_response=None):
        renderer.finish(drain=True)
        if self.settings.active_conversation.pull_events():
          file_repo.save(self.settings.active_conversation)
        done_event.set()

      task.on(TaskEvent.COMPLETE, on_complete)
      task.on(TaskEvent.ERROR, on_error)
      task.on(TaskEvent.CANCELLED, on_cancelled)
      task.on(TaskEvent.ARTIFACT, on_artifact)

      self.registry.add_task(task)
      done_event.wait()

      if error_holder[0]:
        return Result(success=False, message=f"Query failed: {error_holder[0]}")
      return Result(success=True)

    except Exception as e:
      self.logger.error(f"Error processing query: {e}", exc_info=True)
      return Result(success=False, message=f"Error processing query: {str(e)}")
