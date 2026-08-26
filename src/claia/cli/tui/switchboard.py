"""
Tracks and the switchboard: multiple conversations on one screen.

A ``Track`` is the per-conversation accumulator: it owns its
conversation, its transcript widget, the live turn's pacer, the
in-flight task, one queued pending message, and an
unseen-completion flag. Tracks keep accumulating whether or not
they are displayed.

The ``Switchboard`` owns the tracks. Each submit's task callbacks
close over their track, so posted block events route to the right
accumulator by construction. One track is bound to the screen by
toggling transcript display — hopping rebinds the view, never
replays the wire. Tracks are created lazily: launch binds the
active conversation; a hop to an unseen conversation replays its
history once through ``replay_turn``. After any action runs,
:meth:`reconcile` compares ``settings.active_conversation`` with
the bound track and rebinds/creates as needed, so ``conversation
new``/``load`` just work with no command interception.
"""

# External dependencies
import asyncio
import logging
from typing import Dict, List, Optional

from textual.message import Message

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
from .pacer import Pacer
from .status import StatusBar
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

  def __init__(self, track: "Track", events: List[BlockEvent]) -> None:
    super().__init__()
    self.track = track
    self.events = events



########################################################################
#                                TRACK                                 #
########################################################################
class Track:
  """Per-conversation accumulator; keeps growing while hidden."""

  def __init__(self, transcript: Transcript, conversation=None):
    self.conversation = conversation
    self.transcript = transcript
    self.pacer: Optional[Pacer] = None
    self.task: Optional[Task] = None
    self.live_turn: Optional[TurnView] = None
    self.pending: Optional[str] = None
    self.unseen = False
    self.last_turn: Optional[str] = None

  @property
  def busy(self) -> bool:
    return self.task is not None



########################################################################
#                             SWITCHBOARD                              #
########################################################################
class Switchboard:
  """Owns the tracks; binds one to the screen; routes the streams."""

  def __init__(self, app):
    self._app = app
    self._store = JsonStore(app.settings.files_directory)
    self._deliver_lock = asyncio.Lock()
    self.tracks: List[Track] = []
    self.bound: Optional[Track] = None
    self.closing = False

  # ── Lifecycle ────────────────────────────────────────────────────

  async def initialize(self) -> None:
    """Create and bind the launch track (the active conversation)."""
    conversation = getattr(self._app.settings, "active_conversation", None)
    track = await self.create(conversation, replay=conversation is not None)
    self.bind(track)

  async def create(self, conversation, replay: bool = False) -> Track:
    """Mount a hidden transcript and wrap it in a new track."""
    transcript = Transcript()
    transcript.display = False
    track = Track(transcript, conversation)
    self.tracks.append(track)
    await self._app.query_one("#tracks").mount(transcript)
    if replay:
      await self._replay(track)
    return track

  def bind(self, track: Track) -> None:
    """Show ``track`` and make its conversation the active one."""
    self.bound = track
    self._app.settings.active_conversation = track.conversation
    for other in self.tracks:
      other.transcript.display = other is track
    track.unseen = False
    self.refresh_status()

  def hop(self, step: int) -> None:
    """Bind the next/previous track in creation order."""
    if len(self.tracks) < 2:
      return
    index = self.tracks.index(self.bound)
    self.bind(self.tracks[(index + step) % len(self.tracks)])

  async def reconcile(self) -> None:
    """Re-align the bound track with ``settings.active_conversation``.

    Runs after every action: ``conversation new`` drops the active
    conversation (bind a fresh track), ``conversation load`` swaps
    it (bind the matching track, creating and replaying one for a
    conversation the screen has not seen). When a track already
    owns the conversation, its live object wins over a reload from
    disk.
    """
    active = getattr(self._app.settings, "active_conversation", None)
    bound = self.bound
    if active is None:
      if bound.conversation is not None:
        track = next(
          (t for t in self.tracks if t.conversation is None), None,
        )
        if track is None:
          track = await self.create(None)
        self.bind(track)
    else:
      match = next(
        (
          t for t in self.tracks
          if t.conversation is not None and t.conversation.id == active.id
        ),
        None,
      )
      if match is None:
        match = await self.create(active, replay=True)
      if match is not bound or match.conversation is not active:
        self.bind(match)
    self.refresh_status()

  def cancel_all(self) -> None:
    """Cancel every in-flight task and drop queued messages."""
    self.closing = True
    for track in self.tracks:
      track.pending = None
      if track.task is not None:
        track.task.request_cancel()

  # ── Task lifecycle ───────────────────────────────────────────────

  async def submit(self, track: Track, text: str) -> None:
    """Start a turn on ``track``: record the user line, wire the
    task, enqueue. Mirrors the one-shot query wiring; callbacks
    close over the track so events route home from any thread."""
    app = self._app
    task = prepare_query_task(app.settings, text, track.conversation)
    track.conversation = task.conversation
    router = StreamRouter(
      stream_tag_specs(app.registry, task.parameters.get("model_id"))
    )
    store = self._store

    track.transcript.add_user(text)
    track.live_turn = await track.transcript.begin_turn(
      self._assistant_label()
    )
    track.pacer = Pacer()
    track.task = task
    app.resume_pacing()
    self.refresh_status()

    def persist():
      # Save only when domain events indicate mutations; by now the
      # conversation already reflects every tool result and utility.
      if task.conversation.pull_events():
        if not store.save(task.conversation):
          logger.error("Failed to save conversation")

    def post(events):
      events = list(events)
      if events:
        app.post_message(StreamBlocks(track, events))

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

    app.registry.add_task(task)

  async def receive(self, track: Track, events: List[BlockEvent]) -> None:
    """Feed posted events through the track's pacer."""
    if track.pacer is None:
      return
    released = track.pacer.feed(events)
    if released:
      await self._deliver(track, released)

  async def tick(self) -> bool:
    """Tick every live pacer; True while any track is still live."""
    for track in list(self.tracks):
      pacer = track.pacer
      if pacer is None:
        continue
      events = pacer.tick()
      if events:
        await self._deliver(track, events)
    return any(track.pacer is not None for track in self.tracks)

  async def _deliver(self, track: Track, events: List[BlockEvent]) -> None:
    # Ticks and cancel flushes interleave on the loop; the lock keeps
    # event order intact across await points.
    async with self._deliver_lock:
      for event in events:
        turn = track.live_turn
        if turn is None:
          return
        await turn.handle(event)
        if isinstance(event, StreamEnd):
          await self._end_turn(track, event)

  async def _end_turn(self, track: Track, end: StreamEnd) -> None:
    track.pacer = None
    track.live_turn = None
    track.task = None
    track.last_turn = stream_summary(end)
    if end.error:
      self._app.notify(str(end.error), severity="error")
    if track is not self.bound:
      track.unseen = True
    self.refresh_status()

    if track.pending is not None and not self.closing:
      text, track.pending = track.pending, None
      await self.submit(track, text)

  # ── Status ───────────────────────────────────────────────────────

  def refresh_status(self) -> None:
    """Render the bound track's context into the status bar."""
    settings = self._app.settings
    bar = self._app.query_one(StatusBar)
    track = self.bound
    conversation = track.conversation
    label = None
    if conversation is not None:
      label = conversation.title or conversation.id[:8]
    bar.set_context(
      getattr(settings, "active_model", None),
      getattr(settings, "active_agent", None),
      label,
    )
    bar.set_tracks(self.tracks.index(track) + 1, len(self.tracks))
    bar.set_unseen(sum(1 for t in self.tracks if t.unseen))
    bar.set_state("streaming" if track.busy else "idle")
    bar.set_last_turn(track.last_turn)

  # ── Replay ───────────────────────────────────────────────────────

  async def _replay(self, track: Track) -> None:
    """Rebuild the track's prior turns from its conversation.

    Consecutive same-label assistant messages (the rounds of one
    multi-round task) merge into one turn view, so a replayed
    conversation matches its live rendering by construction.
    """
    transcript = track.transcript
    thread = track.conversation.get_thread(include_utility=True)

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
    agent = getattr(self._app.settings, "active_agent", None)
    return (agent or MessageRole.ASSISTANT.value).upper()
