"""
The CLAIA Textual app: tracks over one screen, a live composer,
an action lane, and a status bar.

Conversations are tracks owned by a switchboard: every track keeps
accumulating (paced turn views, per-track queued message) whether
or not it is bound to the screen, and one app timer drips every
live pacer. The composer routes by prefix — ``:`` mints an action
for the serial lane (``Commands.run`` untouched), anything else is
a chat submit into the bound track. Task wiring mirrors the
one-shot query path but never blocks the UI loop: ``TaskEvent``
callbacks (worker threads) post block events into the app, and all
widget mutation happens on the UI thread.
"""

# External dependencies
from typing import Dict, List, Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.timer import Timer

# Internal dependencies
from ..commands import Commands
from .actions import (
  Action,
  ActionFinished,
  ActionLane,
  ActionStarted,
  ActionState,
)
from .composer import Composer, ComposerBar
from .help import HelpScreen
from .ledger import Ledger
from .log_bridge import LogNotice, install, restore
from .pacer import TICK
from .seam import Seam
from .status import StatusBar
from .switchboard import StreamBlocks, Switchboard
from .theme import EXOFOX_DARK, EXOFOX_LIGHT



########################################################################
#                              CONSTANTS                               #
########################################################################
# Every command opens the ledger — its record is the feedback —
# except these, whose payoff is on the main screen. ``None``
# matches any subcommand.
LEDGER_QUIET = {
  ("conversation", "new"),
  ("conversation", "load"),
  ("quit", None),
}



########################################################################
#                                 APP                                  #
########################################################################
class ClaiaApp(App):
  """Full-screen chat shell over the session's conversations."""

  TITLE = "CLAIA"

  CSS = """
  * {
    scrollbar-size: 1 1;
  }
  #tracks {
    height: 1fr;
  }

  /* Toasts as stone chips: content-sized, one severity vein. */
  Toast {
    width: auto;
    min-width: 24;
    max-width: 50%;
    padding: 0 2 0 1;
    background: $panel;
    color: $foreground;

    &.-information {
      border-left: outer $user-label;
    }
    &.-warning {
      border-left: outer $warning;
    }
    &.-error {
      border-left: outer $error;
    }
  }
  ToastRack {
    margin: 0 1 2 0;
  }
  """

  BINDINGS = [
    Binding("escape", "cancel_task", "Cancel", show=False,
            id="cancel-task"),
    Binding("ctrl+q", "quit", "Quit", show=False, priority=True,
            id="quit"),
    # Cursor's terminal captures Ctrl+Q; Alt+letter survives
    # everywhere (ESC-prefix), so alt+q is the portable alias.
    Binding("alt+q", "quit", "Quit", show=False, priority=True,
            id="quit-alt"),
    # Alt+letter arrives from real terminals as a printable key
    # (character set), which a focused TextArea would insert;
    # priority routes these to the app before the composer sees
    # them.
    Binding("alt+n", "next_track", "Next track", show=False,
            priority=True, id="next-track"),
    Binding("alt+p", "previous_track", "Previous track", show=False,
            priority=True, id="previous-track"),
    Binding("alt+a", "toggle_actions", "Actions", show=False,
            priority=True, id="toggle-actions"),
    Binding("f1", "help", "Help", show=False, id="help"),
    # Alias for terminals that eat F-keys.
    Binding("alt+h", "help", "Help", show=False, priority=True,
            id="help-alt"),
  ]

  def __init__(self, registry, settings, **kwargs):
    super().__init__(**kwargs)
    # Note: Textual's App reserves ``_registry`` and ``_task``.
    self.registry = registry
    self.settings = settings
    self.switchboard = Switchboard(self)
    self.actions: List[Action] = []
    self.composer_history: List[str] = []
    self._commands = Commands(registry, settings)
    self._lane = ActionLane(self, self._commands, settings)
    self._log_state = None
    self._pace_timer: Optional[Timer] = None

  # ── Layout and theme ─────────────────────────────────────────────

  def compose(self) -> ComposeResult:
    yield Container(id="tracks")
    yield Seam(id="seam")
    yield ComposerBar(history=self.composer_history)
    yield StatusBar(id="status")

  def get_theme_variable_defaults(self) -> Dict[str, str]:
    # Custom variables must resolve under any theme.
    return {"user-label": "#4A8B8C"}

  async def on_mount(self) -> None:
    self.register_theme(EXOFOX_DARK)
    self.register_theme(EXOFOX_LIGHT)
    self.theme = "exofox"
    self._log_state = install(self)
    self._lane.start()
    # One persistent timer: ticks run in the timer's own task, so a
    # stop() from inside a tick would cancel the running tick's work
    # (including a pending queued submit). Pause/resume instead.
    self._pace_timer = self.set_interval(TICK, self._pace_tick, pause=True)
    await self.switchboard.initialize()
    self.query_one(Composer).focus()

  def on_unmount(self) -> None:
    self._lane.stop()
    if self._log_state is not None:
      restore(*self._log_state)
      self._log_state = None

  # ── Actions ──────────────────────────────────────────────────────

  def action_cancel_task(self) -> None:
    track = self.switchboard.bound
    if track is not None and track.task is not None:
      track.task.request_cancel()

  async def action_quit(self) -> None:
    self.switchboard.cancel_all()
    self.exit()

  def action_next_track(self) -> None:
    self.switchboard.hop(1)

  def action_previous_track(self) -> None:
    self.switchboard.hop(-1)

  def action_toggle_actions(self) -> None:
    if isinstance(self.screen, Ledger):
      self.pop_screen()
    else:
      self.push_screen(Ledger())

  def action_help(self) -> None:
    if isinstance(self.screen, HelpScreen):
      self.pop_screen()
    else:
      self.push_screen(HelpScreen())

  def _ledger(self) -> Optional[Ledger]:
    """The ledger screen, when it is the one on top."""
    screen = self.screen
    return screen if isinstance(screen, Ledger) else None

  # ── Composer routing ─────────────────────────────────────────────

  async def on_composer_submitted(
    self, message: Composer.Submitted,
  ) -> None:
    if message.text.startswith(":"):
      accepted = await self._submit_action(message.text)
    else:
      accepted = await self._submit_chat(message.text)
    if accepted:
      message.composer.remember(message.text)
      message.composer.clear()

  async def _submit_chat(self, text: str) -> bool:
    """Chat into the bound track; queue one message while busy.

    A chat accepted from the ledger's composer pops back to the
    transcript — that is where the answer lands.
    """
    track = self.switchboard.bound
    if track.busy:
      if track.pending is not None:
        self.notify(
          "One message is already waiting — let this turn land first.",
          severity="warning",
        )
        return False
      track.pending = text
    else:
      await self.switchboard.submit(track, text)
    if self._ledger() is not None:
      self.pop_screen()
    return True

  async def _submit_action(self, text: str) -> bool:
    """Mint an action from a ``:`` line and hand it to the lane.

    The ledger is the command surface: submitting a command opens
    it (unless the command is on the quiet list — its payoff is
    the main screen) or, when it is already up, prepends the new
    record live. Special cases stay minimal: ``query`` redirects
    to a chat submit (its one-shot wiring blocks a thread),
    ``setup`` is refused (its ``input()`` wizard needs a real
    terminal), and an unknown command fails without running so it
    can never wrap into an implicit query on the lane.
    """
    line = text[1:].strip()
    tokens = line.split()
    if not tokens:
      self.notify(
        "A lonely ':' — try :help for the menu.", severity="warning",
      )
      return False
    name = self._commands.resolve_name(tokens[0])
    if name == "query":
      rest = " ".join(tokens[1:])
      if not rest:
        self.notify(
          "A query needs words — give it something to work with.",
          severity="warning",
        )
        return False
      return await self._submit_chat(rest)

    action = Action(line=line, tokens=tokens)
    self.actions.insert(0, action)
    ledger = self._ledger()
    if ledger is not None:
      ledger.record_add(action)
    if name is None:
      self._refuse_action(
        action, f"No command called '{tokens[0]}' — :help knows the way.",
      )
    elif name == "setup":
      self._refuse_action(
        action, "Setup wants a real terminal — run 'claia setup' in a shell.",
      )
    else:
      self._lane.submit(action)
    if ledger is None and self._opens_ledger(name, tokens):
      self.push_screen(Ledger())
    return True

  @staticmethod
  def _opens_ledger(name: Optional[str], tokens: List[str]) -> bool:
    sub = tokens[1] if len(tokens) > 1 else None
    return (
      (name, sub) not in LEDGER_QUIET
      and (name, None) not in LEDGER_QUIET
    )

  def _refuse_action(self, action: Action, message: str) -> None:
    action.fail(message)
    ledger = self._ledger()
    if ledger is not None:
      ledger.record_update(action)
    self.query_one(StatusBar).set_action_failed(True)
    self.notify(message, severity="error")

  # ── Action lane results ──────────────────────────────────────────

  def on_action_started(self, message: ActionStarted) -> None:
    ledger = self._ledger()
    if ledger is not None:
      ledger.record_update(message.action)

  async def on_action_finished(self, message: ActionFinished) -> None:
    action = message.action
    ledger = self._ledger()
    if ledger is not None:
      ledger.record_update(action)
    failed = action.state is ActionState.FAILED
    self.query_one(StatusBar).set_action_failed(failed)
    if failed:
      self.notify(
        action.message or "That didn't go as planned.", severity="error",
      )
    if message.result.is_exit():
      self.switchboard.cancel_all()
      self.exit()
      return
    await self.switchboard.reconcile()

  # ── Stream delivery ──────────────────────────────────────────────

  async def on_stream_blocks(self, message: StreamBlocks) -> None:
    await self.switchboard.receive(message.track, message.events)

  def resume_pacing(self) -> None:
    if self._pace_timer is not None:
      self._pace_timer.resume()

  async def _pace_tick(self) -> None:
    live = await self.switchboard.tick()
    if not live and self._pace_timer is not None:
      self._pace_timer.pause()

  # ── Notifications ────────────────────────────────────────────────

  def on_log_notice(self, message: LogNotice) -> None:
    self.notify(message.text, severity=message.severity)
