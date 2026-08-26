"""
Headless TUI tests: real end-to-end turns through ``ClaiaApp``.

A real ``Registry`` (with workers) serves the in-repo dummy model,
so submits exercise the full path: composer → task queue → worker
threads → ``StreamRouter`` → pacer → turn views. The dummy
architecture's module constants are patched per test to control
story content and pace; ``unload_all_models`` forces a fresh
instance so the new story takes effect. Tool turns dispatch the
real ``sample.echo`` tool with ``MAX_TOOL_ROUNDS`` pinned to one.

Phase-4 coverage drives the switchboard (two concurrent tracks,
hopping, unseen badges), per-track queueing, and the ``:`` action
lane (ledger records, reconciliation, quit, serial ordering).
"""

import json
import logging
import time
from types import SimpleNamespace

import pytest
from textual.widgets import Markdown

import claia.core.architectures.dummy.dummy as dummy_module
from claia.core.data import Conversation
from claia.core.enums.conversation import MessageRole
from claia.core.enums.task import TaskStatus
from claia.framework.agents.base import BaseAgent
from claia.framework.registry import Registry

from claia.cli.storage import JsonStore
from claia.cli.tui import ClaiaApp
from claia.cli.tui.actions import ActionState
from claia.cli.tui.composer import Composer
from claia.cli.tui.help import HelpScreen
from claia.cli.tui.ledger import ActionRecord, Ledger
from claia.cli.tui.seam import Phase, Seam
from claia.cli.tui.status import StatusBar, StatusLine
from claia.cli.tui.turn import ToolBlock, TurnLabel, TurnView


SHORT_STORY = "Hello from the dummy model."
TOOL_STORY = (
  "Let me check.<think>quietly</think>"
  '[TOOL_CALL]{"name": "sample.echo", "parameters": {"message": "ping"}}'
  "[/TOOL_CALL] All done."
)
FAST = 1_000_000  # chars/second: effectively instant streaming
SLOW = 400        # chars/second: a comfortably long live window


########################################################################
#                               FIXTURES                               #
########################################################################
@pytest.fixture(scope="module")
def tui_registry():
  """One loaded registry with running workers for the whole module."""
  registry = Registry()
  registry.load_plugins()
  registry.start_workers(2)
  yield registry
  registry.stop_workers()


@pytest.fixture
def set_dummy(monkeypatch, tui_registry):
  """Patch the dummy model's story/pace and force a fresh instance."""
  def _set(story, chars_per_second=FAST, chars_per_chunk=20):
    monkeypatch.setattr(dummy_module, "STORY", story)
    monkeypatch.setattr(dummy_module, "CHARS_PER_SECOND", chars_per_second)
    monkeypatch.setattr(dummy_module, "CHARS_PER_CHUNK", chars_per_chunk)
    tui_registry.unload_all_models()
  return _set


@pytest.fixture
def tui_settings(tmp_path):
  """Minimal settings surface the TUI touches."""
  return SimpleNamespace(
    files_directory=str(tmp_path / "storage"),
    active_model="dummy-model",
    active_model_source=None,
    default_model="dummy-model",
    active_agent="simple",
    default_agent="simple",
    active_prompt=None,
    active_conversation=None,
    get_user_kwargs=lambda: {},
  )


@pytest.fixture
def app(tui_registry, tui_settings):
  return ClaiaApp(registry=tui_registry, settings=tui_settings)


########################################################################
#                               HELPERS                                #
########################################################################
async def wait_for(pilot, condition, timeout=15.0):
  """Poll ``condition`` between UI pauses until it holds or times out."""
  deadline = time.monotonic() + timeout
  while time.monotonic() < deadline:
    if condition():
      return True
    await pilot.pause(0.05)
  return False


def flatten(app, track=None):
  """(kind, …) tuples for a track's transcript, top to bottom.

  Defaults to the bound track. Markdown segments carry their source,
  thinking/notice/label blocks their text, tool blocks their name,
  pretty args, and result body.
  """
  track = track or app.switchboard.bound
  out = []
  for node in track.transcript.children:
    if isinstance(node, TurnView):
      for child in node.children:
        if isinstance(child, Markdown):
          out.append(("markdown", child.source))
        elif isinstance(child, ToolBlock):
          out.append((
            "tool", child.tool_name, child.args_text, child.result_body,
          ))
        elif child.has_class("turn-thinking"):
          out.append(("thinking", str(child.content)))
        elif child.has_class("turn-notice"):
          out.append(("notice", str(child.content)))
        elif isinstance(child, TurnLabel):
          out.append(("label", child.label))
    elif node.has_class("user-label"):
      out.append(("user-label", str(node.content)))
    elif node.has_class("user-text"):
      out.append(("user-text", str(node.content)))
  return out


def kinds(app, track=None):
  return [item[0] for item in flatten(app, track)]


def texts_of(app, kind, track=None):
  return [item[1] for item in flatten(app, track) if item[0] == kind]


def markdown_size(app, track=None):
  return sum(len(s) for s in texts_of(app, "markdown", track))


def records(app):
  """The session's actions, newest first (the ledger's source)."""
  return list(app.actions)


async def submit(app, pilot, text):
  """Submit ``text`` as if typed and entered (bypasses key latency).

  Uses short timed pauses only: an untimed ``pilot.pause()`` waits
  for full message-queue idle, which blocks until the whole turn
  ends when a stream is in flight. The timed micro-pauses let the
  ``Submitted`` message bubble composer → screen → app and return
  while the stream is still live.
  """
  assert await wait_for(pilot, lambda: bool(app.query(Composer)), 5.0)
  composer = app.query_one(Composer)
  composer.load_text(text)
  composer.post_message(Composer.Submitted(composer, text))
  for _ in range(5):
    await pilot.pause(0.01)


async def act(app, pilot, line, timeout=15.0):
  """Submit a ``:`` action line and wait for its record to settle."""
  await submit(app, pilot, line)

  def settled():
    recs = records(app)
    return bool(recs) and recs[0].state in (
      ActionState.DONE, ActionState.FAILED,
    )

  assert await wait_for(pilot, settled, timeout), f"action never settled: {line}"
  return records(app)[0]


async def wait_idle(app, pilot, timeout=15.0):
  ok = await wait_for(
    pilot, lambda: app.query_one(StatusBar).state == "idle", timeout,
  )
  assert ok, "task never returned to idle"


########################################################################
#                            FULL TURN FLOW                            #
########################################################################
class TestTurnFlow:
  async def test_submit_streams_reply_and_returns_to_idle(
    self, app, tui_settings, set_dummy, tmp_path,
  ):
    set_dummy(SHORT_STORY)
    async with app.run_test() as pilot:
      await pilot.press("h", "i", "enter")
      await pilot.pause()

      flat = flatten(app)
      assert ("user-label", "YOU") in flat
      assert ("user-text", "hi") in flat

      await wait_idle(app, pilot)
      assert ("label", "SIMPLE") in flatten(app)  # live agent label
      assert any(SHORT_STORY in s for s in texts_of(app, "markdown"))

      conversation = tui_settings.active_conversation
      assert conversation is app.switchboard.bound.conversation
      roles = [m.role for m in conversation.messages]
      assert roles == [MessageRole.USER, MessageRole.ASSISTANT]
      # The framework stamps the producing agent on the message.
      assert conversation.messages[1].attributes.get("agent") == "simple"

      # Persistence ran in the worker-side terminal callback.
      saved = tmp_path / "storage" / "conversations" / f"{conversation.id}.json"
      assert saved.exists()

  async def test_thinking_renders_muted_inline(self, app, set_dummy):
    set_dummy("Answer.<think>hidden reasoning</think> More answer.")
    async with app.run_test() as pilot:
      await submit(app, pilot, "hello")
      await wait_idle(app, pilot)

      assert texts_of(app, "thinking") == ["hidden reasoning"]
      assert app.query(".turn-thinking")  # the muted class is applied
      # Thinking splits the text into two markdown segments around it
      # and never leaks into them.
      markdown = texts_of(app, "markdown")
      assert len(markdown) == 2
      assert "Answer." in markdown[0]
      assert "More answer." in markdown[1]
      assert not any("hidden reasoning" in s for s in markdown)

  async def test_prior_messages_render_on_launch(
    self, tui_registry, tui_settings,
  ):
    conversation = Conversation(title="Earlier")
    conversation.add_message(MessageRole.USER, "old question")
    stamped = conversation.add_message(MessageRole.ASSISTANT, "old answer")
    stamped.attributes["agent"] = "writer"
    conversation.add_message(MessageRole.USER, "and this?")
    conversation.add_message(MessageRole.ASSISTANT, "unstamped answer")
    tui_settings.active_conversation = conversation

    app = ClaiaApp(registry=tui_registry, settings=tui_settings)
    async with app.run_test() as pilot:
      await pilot.pause()
      assert flatten(app) == [
        ("user-label", "YOU"), ("user-text", "old question"),
        ("label", "WRITER"), ("markdown", "old answer"),
        ("user-label", "YOU"), ("user-text", "and this?"),
        ("label", "ASSISTANT"), ("markdown", "unstamped answer"),
      ]
      bar = app.query_one(StatusBar)
      assert bar.conversation == "Earlier"
      # A replayed conversation never greets.
      transcript = app.switchboard.bound.transcript
      assert not transcript.has_class("-empty")
      assert not transcript.query(".transcript-greeting")


########################################################################
#                              TOOL TURNS                              #
########################################################################
class TestToolTurns:
  async def test_tool_turn_segments_mount_in_order(
    self, app, set_dummy, monkeypatch,
  ):
    monkeypatch.setattr(BaseAgent, "MAX_TOOL_ROUNDS", 1)
    set_dummy(TOOL_STORY)
    async with app.run_test() as pilot:
      await submit(app, pilot, "run the check")
      await wait_idle(app, pilot)

      assert kinds(app) == [
        "user-label", "user-text",
        "label", "markdown", "thinking", "tool", "markdown",
      ]
      flat = flatten(app)
      tool = next(item for item in flat if item[0] == "tool")
      assert tool[1] == "sample.echo"
      assert tool[2] == json.dumps({"message": "ping"}, indent=2)
      assert tool[3] == "ping"  # live result attached from ARTIFACT
      # The result preview renders regardless of when the result
      # landed relative to the block's mount (same-tick delivery).
      block = app.query(ToolBlock).first()
      assert block.has_class("-has-result")
      assert str(block._result_preview.content).startswith("→ ping")
      markdown = texts_of(app, "markdown")
      assert "Let me check." in markdown[0]
      assert "All done." in markdown[1]
      # Raw tag delimiters never hit the screen.
      assert not any("[TOOL_CALL]" in s for s in markdown)

  async def test_stream_end_closes_the_live_turn(self, app, set_dummy):
    set_dummy(SHORT_STORY)
    async with app.run_test() as pilot:
      await submit(app, pilot, "go")
      await wait_idle(app, pilot)
      track = app.switchboard.bound
      assert track.live_turn is None
      assert track.pacer is None
      view = app.query(TurnView).last()
      assert view._stream is None  # the markdown stream was stopped


########################################################################
#                                RELOAD                                #
########################################################################
class TestReload:
  async def test_reload_renders_identical_widget_sequence(
    self, app, tui_registry, tui_settings, set_dummy, monkeypatch,
  ):
    monkeypatch.setattr(BaseAgent, "MAX_TOOL_ROUNDS", 1)
    set_dummy(TOOL_STORY)
    async with app.run_test() as pilot:
      await submit(app, pilot, "run the check")
      await wait_idle(app, pilot)
      live = flatten(app)

    store = JsonStore(tui_settings.files_directory)
    loaded = store.load(tui_settings.active_conversation.id)
    assert loaded is not None
    utilities = [
      m for m in loaded.get_thread(include_utility=True)
      if m.role is MessageRole.UTILITY
    ]
    assert len(utilities) == 2  # the thinking span and the tool call

    fresh = SimpleNamespace(
      files_directory=tui_settings.files_directory,
      active_model="dummy-model",
      active_model_source=None,
      default_model="dummy-model",
      active_agent="simple",
      default_agent="simple",
      active_prompt=None,
      active_conversation=loaded,
      get_user_kwargs=lambda: {},
    )
    reloaded = ClaiaApp(registry=tui_registry, settings=fresh)
    async with reloaded.run_test() as pilot:
      await pilot.pause()
      assert flatten(reloaded) == live


########################################################################
#                      LIVE COMPOSER AND QUEUEING                      #
########################################################################
class TestBusyComposer:
  async def test_composer_stays_editable_mid_stream(
    self, app, set_dummy,
  ):
    set_dummy("stream " * 200, chars_per_second=SLOW)
    async with app.run_test() as pilot:
      await submit(app, pilot, "go")
      bar = app.query_one(StatusBar)
      assert await wait_for(pilot, lambda: bar.state == "streaming")

      await pilot.press("n", "e", "x", "t")
      composer = app.query_one(Composer)
      assert composer.text == "next"
      assert bar.state == "streaming"

      await pilot.press("escape")
      await wait_idle(app, pilot)

  async def test_queued_submit_runs_after_turn_end(
    self, app, tui_settings, set_dummy,
  ):
    set_dummy(SHORT_STORY * 40, chars_per_second=2000)
    async with app.run_test() as pilot:
      await submit(app, pilot, "first")
      bar = app.query_one(StatusBar)
      assert await wait_for(pilot, lambda: bar.state == "streaming")

      await submit(app, pilot, "second")
      # Still one task in flight; the second message is queued, and
      # a third submit is refused while the slot is taken.
      assert bar.state == "streaming"
      assert texts_of(app, "user-label") == ["YOU"]
      await submit(app, pilot, "third")
      assert app.switchboard.bound.pending == "second"

      done = await wait_for(
        pilot,
        lambda: bar.state == "idle"
        and len(tui_settings.active_conversation.messages) == 4,
        timeout=30.0,
      )
      assert done, "queued message never completed"
      roles = [m.role for m in tui_settings.active_conversation.messages]
      assert roles == [
        MessageRole.USER, MessageRole.ASSISTANT,
        MessageRole.USER, MessageRole.ASSISTANT,
      ]
      assert texts_of(app, "user-label") == ["YOU", "YOU"]
      user_texts = texts_of(app, "user-text")
      assert "second" in user_texts
      assert "third" not in user_texts


########################################################################
#                                CANCEL                                #
########################################################################
class TestCancel:
  async def test_escape_cancels_the_inflight_task(
    self, app, tui_settings, set_dummy,
  ):
    set_dummy("long story " * 500, chars_per_second=SLOW)
    async with app.run_test() as pilot:
      await submit(app, pilot, "go")
      bar = app.query_one(StatusBar)
      assert await wait_for(pilot, lambda: bar.state == "streaming")
      task = app.switchboard.bound.task

      await pilot.press("escape")
      await wait_idle(app, pilot)

      assert task.status is TaskStatus.CANCELLED
      assert ("notice", "— cancelled") in flatten(app)
      assert app.switchboard.bound.task is None

      # The shell is still usable: a fresh fast turn completes.
      set_dummy(SHORT_STORY)
      await submit(app, pilot, "again")
      await wait_idle(app, pilot)
      assert any(SHORT_STORY in s for s in texts_of(app, "markdown"))


########################################################################
#                             FOLLOW-TAIL                              #
########################################################################
class TestFollowTail:
  async def test_scrolled_up_view_does_not_jump_on_new_chunks(
    self, app, set_dummy,
  ):
    # Blank lines keep each "line" its own markdown paragraph so the
    # transcript grows tall instead of wrapping one paragraph.
    story = "line\n\n" * 400
    set_dummy(story, chars_per_second=2000, chars_per_chunk=40)
    async with app.run_test() as pilot:
      await submit(app, pilot, "go")
      transcript = app.switchboard.bound.transcript

      # Anchored: the pane follows the tail while content grows.
      assert await wait_for(
        pilot,
        lambda: transcript.max_scroll_y > 10
        and transcript.scroll_y == transcript.max_scroll_y,
      )

      # A user scroll releases the anchor; new chunks must not yank.
      transcript.scroll_up(animate=False)
      await pilot.pause()
      held = transcript.scroll_y
      grown = await wait_for(
        pilot, lambda: transcript.max_scroll_y > held + 10,
      )
      assert grown, "stream never outgrew the held scroll position"
      assert transcript.scroll_y == held

      # Scrolling back to the bottom re-engages the anchor.
      transcript.scroll_end(animate=False)
      await pilot.pause()
      assert await wait_for(
        pilot,
        lambda: transcript.scroll_y == transcript.max_scroll_y
        and transcript.max_scroll_y > held + 10,
      )

      await pilot.press("escape")
      await wait_idle(app, pilot)


########################################################################
#                             SWITCHBOARD                              #
########################################################################
class TestSwitchboard:
  async def test_two_tracks_stream_and_badge_hidden_completion(
    self, app, set_dummy,
  ):
    set_dummy("stream " * 400, chars_per_second=600)
    async with app.run_test() as pilot:
      sb = app.switchboard
      bar = app.query_one(StatusBar)

      await submit(app, pilot, "first topic")
      track_a = sb.bound
      assert await wait_for(pilot, lambda: track_a.task is not None)

      # conversation new rebinds to a fresh track mid-stream.
      await submit(app, pilot, ":conversation new")
      assert await wait_for(pilot, lambda: sb.bound is not track_a)
      track_b = sb.bound
      assert len(sb.tracks) == 2
      assert len(bar.dots) == 2
      assert flatten(app, track_b) == []

      await submit(app, pilot, "second topic")
      assert await wait_for(pilot, lambda: track_b.task is not None)
      assert track_a.task is not None  # still streaming while hidden

      # Both tracks accumulate concurrently, hidden or not.
      assert await wait_for(
        pilot,
        lambda: markdown_size(app, track_a) > 40
        and markdown_size(app, track_b) > 40,
        timeout=30.0,
      )

      # Hop rebinds the view: same widgets, no replay, live growth.
      views_before = list(track_a.transcript.query(TurnView))
      size_at_hop = markdown_size(app, track_a)
      await pilot.press("alt+n")
      assert sb.bound is track_a
      assert track_a.transcript.display
      assert not track_b.transcript.display
      assert list(track_a.transcript.query(TurnView)) == views_before
      assert await wait_for(
        pilot,
        lambda: markdown_size(app, track_a) > size_at_hop,
        timeout=30.0,
      )

      # The hidden track's completion sets the badge…
      assert await wait_for(
        pilot,
        lambda: track_b.task is None and track_b.pacer is None,
        timeout=60.0,
      )
      assert track_b.unseen
      assert sum(1 for d in bar.dots if d.unseen) == 1

      # …and binding it clears the badge.
      await pilot.press("alt+n")
      assert sb.bound is track_b
      assert not track_b.unseen
      assert sum(1 for d in bar.dots if d.unseen) == 0

      assert await wait_for(
        pilot,
        lambda: track_a.task is None and track_a.pacer is None,
        timeout=60.0,
      )

  async def test_idle_track_accepts_while_another_streams(
    self, app, set_dummy,
  ):
    set_dummy("stream " * 300, chars_per_second=SLOW)
    async with app.run_test() as pilot:
      sb = app.switchboard
      await submit(app, pilot, "keep going")
      track_a = sb.bound
      assert await wait_for(pilot, lambda: track_a.task is not None)

      await submit(app, pilot, ":conversation new")
      assert await wait_for(pilot, lambda: sb.bound is not track_a)
      track_b = sb.bound
      assert track_b.task is None  # idle: a submit starts immediately

      await submit(app, pilot, "start the second")
      assert await wait_for(pilot, lambda: track_b.task is not None)
      assert track_a.task is not None
      assert app.query_one(StatusBar).state == "streaming"

      # Queueing is per track: B takes one pending while A streams.
      await submit(app, pilot, "queued on b")
      assert track_b.pending == "queued on b"
      assert track_a.pending is None

      track_a.task.request_cancel()
      track_b.task.request_cancel()
      assert await wait_for(
        pilot,
        lambda: all(t.task is None and t.pacer is None for t in sb.tracks),
        timeout=30.0,
      )


########################################################################
#                               ACTIONS                                #
########################################################################
class TestActions:
  async def test_model_list_lands_in_ledger_not_transcript(self, app):
    async with app.run_test() as pilot:
      action = await act(app, pilot, ":model list")
      assert action.state is ActionState.DONE
      assert action.line == "model list"
      assert "dummy" in (action.output or "").lower()
      assert action.format == "markdown"
      assert flatten(app) == []  # command output never hits the transcript
      assert len(records(app)) == 1
      assert not app.query_one(StatusBar).action_failed

  async def test_conversation_new_rebinds_to_fresh_track(
    self, app, tui_settings, set_dummy,
  ):
    set_dummy(SHORT_STORY)
    async with app.run_test() as pilot:
      await submit(app, pilot, "hi")
      await wait_idle(app, pilot)
      sb = app.switchboard
      first = sb.bound
      assert first.conversation is not None

      action = await act(app, pilot, ":conversation new")
      assert action.state is ActionState.DONE
      assert await wait_for(pilot, lambda: sb.bound is not first)
      assert sb.bound.conversation is None
      assert tui_settings.active_conversation is None
      assert flatten(app) == []          # a fresh transcript is bound
      assert flatten(app, first) != []   # the old track kept its content

      # Running it again on the already-fresh track changes nothing.
      await act(app, pilot, ":conversation new")
      assert len(sb.tracks) == 2

  async def test_conversation_load_creates_and_replays(
    self, app, tui_settings,
  ):
    conversation = Conversation(title="Stored")
    conversation.add_message(MessageRole.USER, "old question")
    stamped = conversation.add_message(MessageRole.ASSISTANT, "stored answer")
    stamped.attributes["agent"] = "writer"
    JsonStore(tui_settings.files_directory).save(conversation)

    async with app.run_test() as pilot:
      sb = app.switchboard
      action = await act(app, pilot, f":conversation load {conversation.id}")
      assert action.state is ActionState.DONE
      assert await wait_for(
        pilot,
        lambda: sb.bound.conversation is not None
        and sb.bound.conversation.id == conversation.id,
      )
      assert len(sb.tracks) == 2
      assert flatten(app) == [
        ("user-label", "YOU"), ("user-text", "old question"),
        ("label", "WRITER"), ("markdown", "stored answer"),
      ]
      bar = app.query_one(StatusBar)
      assert bar.conversation == "Stored"
      assert len(bar.dots) == 2

  async def test_unknown_command_fails_with_toast(self, app):
    async with app.run_test() as pilot:
      toasts = []
      original_notify = app.notify
      app.notify = lambda msg, **kw: (
        toasts.append((msg, kw.get("severity"))),
        original_notify(msg, **kw),
      )
      action = await act(app, pilot, ":frobnicate now")
      assert action.state is ActionState.FAILED
      assert "No command called 'frobnicate'" in action.message
      assert any(sev == "error" for _, sev in toasts)
      assert app.query_one(StatusBar).action_failed
      assert flatten(app) == []  # it never ran, never chatted

  async def test_setup_is_refused_with_oneshot_pointer(self, app):
    async with app.run_test() as pilot:
      action = await act(app, pilot, ":setup")
      assert action.state is ActionState.FAILED
      assert "claia setup" in action.message

  async def test_query_action_redirects_to_chat(self, app, set_dummy):
    set_dummy(SHORT_STORY)
    async with app.run_test() as pilot:
      await submit(app, pilot, ":query hello there")
      await wait_idle(app, pilot)
      flat = flatten(app)
      assert ("user-text", "hello there") in flat
      assert any(SHORT_STORY in s for s in texts_of(app, "markdown"))
      assert records(app) == []  # the chat turn is the record

  async def test_actions_run_serially_in_order(self, app, monkeypatch):
    calls = []
    original_run = app._commands.run

    def slow_run(tokens, conversation=None):
      calls.append(("start", tokens[0]))
      time.sleep(0.15)
      result = original_run(tokens, conversation)
      calls.append(("end", tokens[0]))
      return result

    monkeypatch.setattr(app._commands, "run", slow_run)
    async with app.run_test() as pilot:
      await submit(app, pilot, ":version")
      await submit(app, pilot, ":model current")

      def all_done():
        recs = records(app)
        return len(recs) == 2 and all(
          r.state is ActionState.DONE for r in recs
        )

      assert await wait_for(pilot, all_done)
      assert calls == [
        ("start", "version"), ("end", "version"),
        ("start", "model"), ("end", "model"),
      ]
      # Newest first in the ledger.
      assert [a.line for a in records(app)] == [
        "model current", "version",
      ]

  async def test_quit_action_cancels_inflight_and_exits(
    self, app, set_dummy,
  ):
    set_dummy("long story " * 500, chars_per_second=SLOW)
    async with app.run_test() as pilot:
      await submit(app, pilot, "go")
      sb = app.switchboard
      assert await wait_for(pilot, lambda: sb.bound.task is not None)
      task = sb.bound.task

      await submit(app, pilot, ":quit")
      assert await wait_for(pilot, lambda: app._exit, 10.0)

    # Cooperative cancel lands on the worker thread shortly after.
    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline and task.status is not TaskStatus.CANCELLED:
      time.sleep(0.05)
    assert task.status is TaskStatus.CANCELLED

  async def test_ledger_page_toggles_with_alt_a(self, app):
    async with app.run_test() as pilot:
      assert not isinstance(app.screen, Ledger)
      await pilot.press("alt+a")
      assert isinstance(app.screen, Ledger)
      await pilot.press("alt+a")
      assert not isinstance(app.screen, Ledger)
      await pilot.press("alt+a")
      await pilot.press("escape")
      assert not isinstance(app.screen, Ledger)

  async def test_commands_auto_open_the_ledger(self, app):
    async with app.run_test() as pilot:
      await act(app, pilot, ":version")
      assert isinstance(app.screen, Ledger)
      await pilot.press("escape")
      assert not isinstance(app.screen, Ledger)
      # Quiet-listed: its payoff is the fresh transcript, not a record.
      await act(app, pilot, ":conversation new")
      assert not isinstance(app.screen, Ledger)

  async def test_ledger_shows_records_counts_and_markdown(self, app):
    async with app.run_test() as pilot:
      await act(app, pilot, ":model list")   # auto-opens the ledger
      assert isinstance(app.screen, Ledger)
      await act(app, pilot, ":frobnicate")   # prepends live while open
      await pilot.pause()
      recs = list(app.screen.query(ActionRecord))
      assert [r.action.line for r in recs] == ["frobnicate", "model list"]
      assert recs[0].has_class("-failed")
      assert recs[1].has_class("-done")
      # A markdown result renders as a Markdown widget, not raw text.
      assert recs[1].query(Markdown)
      assert not recs[0].query(Markdown)
      heading = app.screen.query_one(TurnLabel)
      assert heading.meta == "2 run · 1 failed"

  async def test_ledger_updates_live_while_open(self, app, monkeypatch):
    original_run = app._commands.run

    def slow_run(tokens, conversation=None):
      time.sleep(0.2)
      return original_run(tokens, conversation)

    monkeypatch.setattr(app._commands, "run", slow_run)
    async with app.run_test() as pilot:
      await submit(app, pilot, ":version")   # auto-opens the ledger
      assert isinstance(app.screen, Ledger)

      def settled():
        recs = list(app.screen.query(ActionRecord))
        return bool(recs) and recs[0].has_class("-done")

      assert await wait_for(pilot, settled)
      assert app.screen.query_one(Seam).phase is Phase.IDLE

  async def test_ledger_composer_chats_back_to_the_transcript(
    self, app, set_dummy,
  ):
    set_dummy(SHORT_STORY)
    async with app.run_test() as pilot:
      await pilot.press("alt+a")
      assert isinstance(app.screen, Ledger)
      ledger_composer = app.screen.query_one(Composer)
      assert app.focused is ledger_composer
      ledger_composer.load_text("hi from the ledger")
      ledger_composer.post_message(
        Composer.Submitted(ledger_composer, "hi from the ledger"),
      )
      assert await wait_for(
        pilot, lambda: not isinstance(app.screen, Ledger),
      )
      await wait_idle(app, pilot)
      flat = flatten(app)
      assert ("user-text", "hi from the ledger") in flat
      assert any(SHORT_STORY in s for s in texts_of(app, "markdown"))
      # The shared history recalls across composers.
      assert app.composer_history == ["hi from the ledger"]


########################################################################
#                          LOGGING OWNERSHIP                           #
########################################################################
class TestLoggingOwnership:
  async def test_warning_becomes_toast_and_never_hits_stdout(
    self, app, set_dummy, capsys,
  ):
    set_dummy(SHORT_STORY)
    root = logging.getLogger()
    console = logging.StreamHandler()
    root.addHandler(console)
    try:
      toasts = []
      async with app.run_test() as pilot:
        original_notify = app.notify
        app.notify = lambda msg, **kw: (
          toasts.append((msg, kw.get("severity"))),
          original_notify(msg, **kw),
        )
        assert console not in root.handlers

        await submit(app, pilot, "go")
        logging.getLogger("claia.test").warning("mid-turn warning")
        await wait_idle(app, pilot)
        assert await wait_for(pilot, lambda: len(toasts) > 0, timeout=5.0)
        assert ("mid-turn warning", "warning") in toasts

      # Console handlers come back once the app exits.
      assert console in root.handlers
      captured = capsys.readouterr()
      assert "mid-turn warning" not in captured.out
      assert "mid-turn warning" not in captured.err
    finally:
      root.removeHandler(console)


########################################################################
#                             PRESENTATION                             #
########################################################################
class TestPresentation:
  async def test_greeting_shows_until_first_content(self, app, set_dummy):
    set_dummy(SHORT_STORY)
    async with app.run_test() as pilot:
      await pilot.pause()
      transcript = app.switchboard.bound.transcript
      assert transcript.has_class("-empty")
      assert transcript.query(".transcript-greeting")

      await submit(app, pilot, "hi")
      await wait_idle(app, pilot)
      assert not transcript.has_class("-empty")
      assert not transcript.query(".transcript-greeting")

  async def test_seam_follows_the_turn_and_flashes_on_cancel(
    self, app, set_dummy,
  ):
    set_dummy("stream " * 200, chars_per_second=SLOW)
    async with app.run_test() as pilot:
      seam = app.query_one(Seam)
      assert seam.phase is Phase.IDLE

      await submit(app, pilot, "go")
      assert await wait_for(pilot, lambda: seam.phase is Phase.STREAMING)

      await pilot.press("escape")
      await wait_idle(app, pilot)
      assert seam.phase is Phase.IDLE
      assert seam._flash_kind == "warning"

  async def test_tool_pulse_settles_when_the_turn_ends(
    self, app, set_dummy, monkeypatch,
  ):
    monkeypatch.setattr(BaseAgent, "MAX_TOOL_ROUNDS", 1)
    set_dummy(TOOL_STORY)
    async with app.run_test() as pilot:
      await submit(app, pilot, "run the check")
      await wait_idle(app, pilot)

      block = app.query(ToolBlock).first()
      assert block._settled
      assert block._pulse_timer is None
      assert block._title.styles.text_opacity == 1.0

  async def test_status_cluster_shows_identity_glyph(self, app):
    async with app.run_test() as pilot:
      await pilot.pause()
      line = app.query_one(StatusLine).render().plain
      assert line.startswith("◆ ")
      assert "simple" in line
      assert "dummy-model" in line

  async def test_help_card_toggles(self, app):
    async with app.run_test() as pilot:
      await pilot.pause()
      await pilot.press("f1")
      assert isinstance(app.screen, HelpScreen)
      await pilot.press("escape")
      await pilot.pause()
      assert not isinstance(app.screen, HelpScreen)
      # F1 toggles closed from the app binding too.
      await pilot.press("f1")
      assert isinstance(app.screen, HelpScreen)
      await pilot.press("f1")
      await pilot.pause()
      assert not isinstance(app.screen, HelpScreen)
