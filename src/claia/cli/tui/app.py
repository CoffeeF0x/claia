"""
The CLAIA Textual app: one conversation, a live composer, paced
turn-view rendering, and a status bar.

Task wiring mirrors the one-shot query path but never blocks the
UI loop: submit goes through ``registry.add_task`` and every
``TaskEvent`` callback (fired on worker threads) is marshalled
into the app as a posted message — all widget mutation happens on
the UI thread. Posted block events pass through a per-turn
``Pacer`` (a ~40ms timer drips text, structural events are
barriers) before reaching the live ``TurnView``; reloaded history
replays through the same turn pipeline instantly. Persistence
(``pull_events`` → ``JsonStore.save``) stays in the terminal
callbacks on the worker thread, exactly as in ``QueryCommand``.
"""

# External dependencies
import asyncio
import logging
from typing import Dict, List, Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.timer import Timer

# Internal dependencies
from ...core.data.artifacts import ToolArtifact
from ...core.enums.conversation import MessageRole
from ...core.enums.task import TaskEvent, TaskStatus
from ...framework.task import Task
from ..renderer import stream_summary
from ..storage import JsonStore
from ..stream import (
  BlockEvent,
  StreamEnd,
  StreamRouter,
  ToolResult,
  replay_turn,
)
from ..utils import prepare_query_task, stream_tag_specs
from .composer import Composer
from .log_bridge import LogNotice, install, restore
from .pacer import TICK, Pacer
from .status import StatusBar
from .theme import EXOFOX_DARK, EXOFOX_LIGHT
from .transcript import Transcript
from .turn import TurnView



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



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
    Binding("escape", "cancel_task", "Cancel", show=False,
            id="cancel-task"),
    Binding("ctrl+q", "quit", "Quit", show=False, priority=True,
            id="quit"),
    # Cursor's terminal captures Ctrl+Q; Alt+letter survives
    # everywhere (ESC-prefix), so alt+q is the portable alias.
    Binding("alt+q", "quit", "Quit", show=False, priority=True,
            id="quit-alt"),
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
    self._live_turn: Optional[TurnView] = None
    self._pacer: Optional[Pacer] = None
    self._pace_timer: Optional[Timer] = None
    self._deliver_lock = asyncio.Lock()

  # ── Layout and theme ─────────────────────────────────────────────

  def compose(self) -> ComposeResult:
    yield Transcript(id="transcript")
    yield Composer(id="composer")
    yield StatusBar(id="status")

  def get_theme_variable_defaults(self) -> Dict[str, str]:
    # Custom variables must resolve under any theme.
    return {"user-label": "#4A8B8C"}

  async def on_mount(self) -> None:
    self.register_theme(EXOFOX_DARK)
    self.register_theme(EXOFOX_LIGHT)
    self.theme = "exofox"
    self._log_state = install(self)
    # One persistent timer: ticks run in the timer's own task, so a
    # stop() from inside a tick would cancel the running tick's work
    # (including a pending queued submit). Pause/resume instead.
    self._pace_timer = self.set_interval(TICK, self._pace_tick, pause=True)
    await self._render_history()
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

  async def on_composer_submitted(
    self, message: Composer.Submitted,
  ) -> None:
    composer = message.composer
    if self._active_task is not None:
      if self._pending is not None:
        self.notify("A message is already queued.", severity="warning")
        return
      self._pending = message.text
    else:
      await self._submit(message.text)
    composer.remember(message.text)
    composer.clear()

  # ── Task lifecycle ───────────────────────────────────────────────

  async def _submit(self, text: str) -> None:
    """Start a turn: record the user line, wire the task, enqueue."""
    task = prepare_query_task(self.settings, text)
    router = StreamRouter(
      stream_tag_specs(self.registry, task.parameters.get("model_id"))
    )
    store = self._store

    transcript = self.query_one(Transcript)
    transcript.add_user(text)
    self._live_turn = await transcript.begin_turn(self._assistant_label())
    self._pacer = Pacer()
    if self._pace_timer is not None:
      self._pace_timer.resume()
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
      if not store.save(artifact):
        logger.error(f"Failed to save artifact for message {message_id}")
        return
      if isinstance(artifact, ToolArtifact) and artifact.is_result:
        post([ToolResult(
          name=artifact.tool_name,
          body=artifact.payload_text(),
          call_id=artifact.call_id,
        )])
      else:
        post(router.feed_artifact(artifact))

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

  async def on_stream_blocks(self, message: StreamBlocks) -> None:
    if self._pacer is None:
      return
    released = self._pacer.feed(message.events)
    if released:
      await self._deliver(released)

  async def _pace_tick(self) -> None:
    if self._pacer is None:
      return
    events = self._pacer.tick()
    if events:
      await self._deliver(events)

  async def _deliver(self, events: List[BlockEvent]) -> None:
    # Ticks and cancel flushes interleave on the loop; the lock keeps
    # event order intact across await points.
    async with self._deliver_lock:
      for event in events:
        turn = self._live_turn
        if turn is None:
          return
        await turn.handle(event)
        if isinstance(event, StreamEnd):
          await self._end_turn(event)

  async def _end_turn(self, end: StreamEnd) -> None:
    if self._pace_timer is not None:
      self._pace_timer.pause()
    self._pacer = None
    self._live_turn = None
    if end.error:
      self.notify(str(end.error), severity="error")

    status = self.query_one(StatusBar)
    status.set_last_turn(stream_summary(end))
    status.set_state("idle")
    self._active_task = None

    if self._pending is not None and not self._exiting:
      text, self._pending = self._pending, None
      await self._submit(text)

  # ── Notifications ────────────────────────────────────────────────

  def on_log_notice(self, message: LogNotice) -> None:
    self.notify(message.text, severity=message.severity)

  # ── Helpers ──────────────────────────────────────────────────────

  async def _render_history(self) -> None:
    """Replay the active conversation's prior turns, if any.

    Consecutive same-label assistant messages (the rounds of one
    multi-round task) merge into one turn view, so a reloaded
    conversation matches its live rendering by construction.
    """
    conversation = getattr(self.settings, "active_conversation", None)
    if conversation is None:
      return
    transcript = self.query_one(Transcript)
    thread = conversation.get_thread(include_utility=True)

    utilities: Dict[str, List] = {}
    for msg in thread:
      if msg.role is MessageRole.UTILITY and msg.source_message_id:
        utilities.setdefault(msg.source_message_id, []).append(msg)

    view: Optional[TurnView] = None
    for msg in thread:
      if msg.role is MessageRole.UTILITY:
        continue
      if msg.role is MessageRole.USER:
        transcript.add_user(msg.content or "")
        view = None
        continue
      label = (msg.attributes.get("agent") or msg.role.value).upper()
      if view is None or view.label != label:
        view = await transcript.begin_turn(label)
      await view.load(replay_turn(msg, utilities.get(msg.message_id, [])))

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
