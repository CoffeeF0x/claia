"""
Headless TUI tests: real end-to-end turns through ``ClaiaApp``.

A real ``Registry`` (with workers) serves the in-repo dummy model,
so submits exercise the full path: composer → task queue → worker
threads → ``StreamRouter`` → pacer → turn views. The dummy
architecture's module constants are patched per test to control
story content and pace; ``unload_all_models`` forces a fresh
instance so the new story takes effect. Tool turns dispatch the
real ``sample.echo`` tool with ``MAX_TOOL_ROUNDS`` pinned to one.
"""

import json
import logging
import time
from types import SimpleNamespace

import pytest
from textual.widgets import Markdown

import claia.core.architectures.dummy.dummy as dummy_module
from claia.core.enums.conversation import MessageRole
from claia.core.enums.task import TaskStatus
from claia.framework.agents.base import BaseAgent
from claia.framework.registry import Registry

from claia.cli.storage import JsonStore
from claia.cli.tui import ClaiaApp
from claia.cli.tui.composer import Composer
from claia.cli.tui.status import StatusBar
from claia.cli.tui.transcript import Transcript
from claia.cli.tui.turn import ToolBlock, TurnView


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


def flatten(app):
  """(kind, …) tuples for every transcript block, top to bottom.

  Markdown segments carry their source, thinking/notice/label blocks
  their text, tool blocks their name, pretty args, and result body.
  """
  out = []
  for node in app.query_one(Transcript).children:
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
        elif child.has_class("turn-label"):
          out.append(("label", str(child.content)))
    elif node.has_class("user-label"):
      out.append(("user-label", str(node.content)))
    elif node.has_class("user-text"):
      out.append(("user-text", str(node.content)))
  return out


def kinds(app):
  return [item[0] for item in flatten(app)]


def texts_of(app, kind):
  return [item[1] for item in flatten(app) if item[0] == kind]


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
    from claia.core.data import Conversation
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
      assert app._live_turn is None
      assert app._pacer is None
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
      assert app._pending == "second"

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
      task = app._active_task

      await pilot.press("escape")
      await wait_idle(app, pilot)

      assert task.status is TaskStatus.CANCELLED
      assert ("notice", "[cancelled]") in flatten(app)
      assert app._active_task is None

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
      transcript = app.query_one(Transcript)

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
