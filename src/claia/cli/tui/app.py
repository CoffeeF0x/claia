"""
The CLAIA Textual app: one conversation, a live composer, a
streamed plain-text tail, and a status bar.

Task wiring mirrors the one-shot query path but never blocks the
UI loop: submit goes through ``registry.add_task`` and every
``TaskEvent`` callback (fired on worker threads) is marshalled
into the app as a posted message — all widget mutation happens on
the UI thread. Persistence (``pull_events`` → ``JsonStore.save``)
stays in the terminal callbacks on the worker thread, exactly as
in ``QueryCommand``.
"""

# External dependencies
import logging
from typing import List, Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.message import Message

# Internal dependencies
from ...core.enums.conversation import MessageRole
from ...core.enums.task import TaskEvent, TaskStatus
from ...framework.task import Task
from ..renderer import stream_summary
from ..storage import JsonStore
from ..stream import (
  ArtifactNotice,
  BlockEvent,
  Channel,
  StreamEnd,
  StreamRouter,
  TextDelta,
  ToolCall,
)
from ..utils import prepare_query_task, stream_tag_specs
from .composer import Composer
from .log_bridge import LogNotice, install, restore
from .status import StatusBar
from .transcript import Transcript



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)

USER_LABEL = "YOU"



########################################################################
#                               MESSAGES                               #
########################################################################
class StreamBlocks(Message):
  """Block events crossing from a worker thread into the UI loop."""

  def __init__(self, events: List[BlockEvent]) -> None:
    super().__init__()
    self.events = events



########################################################################
#                                 APP                                  #
########################################################################
class ClaiaApp(App):
  """Full-screen chat shell over the active conversation."""

  TITLE = "CLAIA"

  BINDINGS = [
    Binding("escape", "cancel_task", "Cancel", show=False),
  ]

  def __init__(self, registry, settings, **kwargs):
    super().__init__(**kwargs)
    # Note: Textual's App reserves ``_registry`` and ``_task``.
    self.registry = registry
    self.settings = settings
    self._store = JsonStore(settings.files_directory)
    self._active_task: Optional[Task] = None
    self._pending: Optional[str] = None
    self._exiting = False
    self._log_state = None

  # ── Layout ───────────────────────────────────────────────────────

  def compose(self) -> ComposeResult:
    yield Transcript(id="transcript")
    yield Composer(id="composer")
    yield StatusBar(id="status")

  def on_mount(self) -> None:
    self._log_state = install(self)
    self._render_history()
    self._refresh_context()
    self.query_one(Composer).focus()

  def on_unmount(self) -> None:
    if self._log_state is not None:
      restore(*self._log_state)
      self._log_state = None

  # ── Actions ──────────────────────────────────────────────────────

  def action_cancel_task(self) -> None:
    if self._active_task is not None:
      self._active_task.request_cancel()

  async def action_quit(self) -> None:
    self._exiting = True
    if self._active_task is not None:
      self._active_task.request_cancel()
    self.exit()

  # ── Composer ─────────────────────────────────────────────────────

  def on_composer_submitted(self, message: Composer.Submitted) -> None:
    composer = message.composer
    if self._active_task is not None:
      if self._pending is not None:
        self.notify("A message is already queued.", severity="warning")
        return
      self._pending = message.text
    else:
      self._submit(message.text)
    composer.remember(message.text)
    composer.clear()

  # ── Task lifecycle ───────────────────────────────────────────────

  def _submit(self, text: str) -> None:
    """Start a turn: record the user line, wire the task, enqueue."""
    task = prepare_query_task(self.settings, text)
    router = StreamRouter(
      stream_tag_specs(self.registry, task.parameters.get("model_id"))
    )
    store = self._store

    transcript = self.query_one(Transcript)
    transcript.add_message(USER_LABEL, text)
    transcript.begin_turn(self._assistant_label())
    self._refresh_context()
    self.query_one(StatusBar).set_state("streaming")

    def persist():
      # Save only when domain events indicate mutations; by now the
      # conversation already reflects every tool result and utility.
      if task.conversation.pull_events():
        if not store.save(task.conversation):
          logger.error("Failed to save conversation")

    def post(events):
      events = list(events)
      if events:
        self.post_message(StreamBlocks(events))

    def on_chunk(chunk):
      post(router.feed(chunk))

    def on_artifact(artifact, message_id):
      if store.save(artifact):
        post(router.feed_artifact(artifact))
      else:
        logger.error(f"Failed to save artifact for message {message_id}")

    def on_complete(_result):
      persist()
      post(router.end(TaskStatus.COMPLETED))

    def on_error(error_msg):
      post(router.end(TaskStatus.FAILED, error=str(error_msg)))

    def on_cancelled(_result=None):
      persist()
      post(router.end(TaskStatus.CANCELLED))

    task.on(TaskEvent.CHUNK, on_chunk)
    task.on(TaskEvent.ARTIFACT, on_artifact)
    task.on(TaskEvent.COMPLETE, on_complete)
    task.on(TaskEvent.ERROR, on_error)
    task.on(TaskEvent.CANCELLED, on_cancelled)

    self._active_task = task
    self.registry.add_task(task)

  def on_stream_blocks(self, message: StreamBlocks) -> None:
    transcript = self.query_one(Transcript)
    for event in message.events:
      if isinstance(event, TextDelta):
        if event.channel is Channel.TEXT:
          transcript.append_stream(event.text)
      elif isinstance(event, ToolCall):
        transcript.add_notice(f"[tool {event.name or 'unknown'}]")
      elif isinstance(event, ArtifactNotice):
        transcript.add_notice(f"[saved: {event.name}]")
      elif isinstance(event, StreamEnd):
        self._end_turn(event)

  def _end_turn(self, end: StreamEnd) -> None:
    transcript = self.query_one(Transcript)
    transcript.end_block()
    if end.status is TaskStatus.CANCELLED:
      transcript.add_notice("[cancelled]")
    if end.error:
      transcript.add_notice(f"[error: {end.error}]")
      self.notify(str(end.error), severity="error")

    status = self.query_one(StatusBar)
    status.set_last_turn(stream_summary(end))
    status.set_state("idle")
    self._active_task = None

    if self._pending is not None and not self._exiting:
      text, self._pending = self._pending, None
      self._submit(text)

  # ── Notifications ────────────────────────────────────────────────

  def on_log_notice(self, message: LogNotice) -> None:
    self.notify(message.text, severity=message.severity)

  # ── Helpers ──────────────────────────────────────────────────────

  def _render_history(self) -> None:
    """Render the active conversation's prior messages, if any."""
    conversation = getattr(self.settings, "active_conversation", None)
    if conversation is None:
      return
    transcript = self.query_one(Transcript)
    for msg in conversation.get_thread():
      if msg.role is MessageRole.USER:
        label = USER_LABEL
      else:
        label = (msg.attributes.get("agent") or msg.role.value).upper()
      transcript.add_message(label, msg.content or "")

  def _assistant_label(self) -> str:
    agent = getattr(self.settings, "active_agent", None)
    return (agent or MessageRole.ASSISTANT.value).upper()

  def _refresh_context(self) -> None:
    conversation = getattr(self.settings, "active_conversation", None)
    label = None
    if conversation is not None:
      label = conversation.title or conversation.id[:8]
    self.query_one(StatusBar).set_context(
      getattr(self.settings, "active_model", None),
      getattr(self.settings, "active_agent", None),
      label,
    )
