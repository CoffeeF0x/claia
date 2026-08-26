# CLI TUI

The interactive face of `claia.cli`: bare `claia` on a TTY opens
this full-screen Textual app. Conversations are tracks owned by a
switchboard — every track keeps accumulating (paced turn views,
one queued message) whether or not it is on screen — with a live
composer that routes chat into the bound track and `:` lines onto
a serial action lane, all in the ExoFox family-look theme. The
presentation is a quiet instrument panel: the kintsugi seam (a
crack of gold between transcript and composer) carries the bound
track's liveness, the composer is boxless behind a prompt glyph
that goes gold with focus, the status bar is a glyph-based cluster
with per-track dots, actions get a full ledger page, and the brand
voice lives in the greeting, the notices, and the toasts (stone
chips with a severity vein).

## What Lives Here

- `app.py` — `ClaiaApp`: layout (and the toast/scrollbar
  restyle), bindings, composer routing (`:` → action, else chat),
  the ledger auto-open policy (`LEDGER_QUIET`), the session's
  action list (`app.actions`, the ledger's source of truth), the
  worker→UI thread bridge, the one pacer timer, action-lane
  outcomes (exit / toast / reconcile), and logging ownership.
- `switchboard.py` — `Track` (per-conversation accumulator:
  conversation, transcript, live pacer/turn, in-flight task, one
  pending message, unseen flag) and `Switchboard` (owns tracks,
  binds one to the screen by display toggling, ticks every live
  pacer, replays history into lazily-created tracks, reconciles
  `settings.active_conversation` after every action, cancels all
  tasks on quit).
- `actions.py` — `Action` (command line, source, state, `Result`
  message/output, timestamps) and `ActionLane`, the one serial
  worker thread feeding `Commands.run` and posting transitions
  back into the UI loop.
- `ledger.py` — `Ledger`, the full-page newest-first record of
  every action and the command surface itself: submitting any
  command opens it (quiet-listed ones excepted), Alt+A toggles,
  Esc returns. Spined by a vertical seam that carries the lane's
  liveness, headed by run/failure counts, and closed by its own
  composer bar — `:` lines prepend their record live, plain text
  chats and returns to the transcript. Plus `ActionRecord`
  (status glyph, command, duration whisper, full output —
  rendered as markdown when the `Result` declares it).
- `transcript.py` — `Transcript`, a scrolling pane of user label
  blocks and `TurnView`s with follow-tail (Textual anchor)
  scrolling; one per track. An empty transcript centers a brand
  greeting, dismissed by the first content.
- `turn.py` — `TurnView` (one per assistant turn: a `TurnLabel`
  heading with a hairline rule and the turn's compact usage meta,
  markdown segments via `Markdown.get_stream`, inline muted
  thinking, notice lines) and `ToolBlock` (gold-guttered
  `Collapsible`: a name line that breathes until its result lands,
  truncated args preview, result preview, full payloads behind
  the toggle — result widgets always compose, hidden behind a
  `-has-result` class, so delivery timing cannot race mounting).
- `seam.py` — `Seam` and `Phase`: the one-cell kintsugi crack,
  horizontal between transcript and composer (the bound track's
  liveness) or vertical as the ledger's spine (the action
  lane's). Gold glints travel it while streaming, amber during a
  tool call or running action, and failures or cancels flash it
  in the semantic color; it owns its own timer, paused whenever
  idle.
- `help.py` — `HelpScreen`, the F1/Alt+H modal card: the key map
  with fallbacks plus a pointer to `:help`.
- `pacer.py` — `Pacer`, the per-turn jitter buffer: text drips
  at an adaptive rate on a ~40ms tick; structural events are
  barriers; graceful ends accelerate the drain, cancel/failure
  flushes instantly. Pure logic, no Textual imports.
- `theme.py` — the ExoFox palette as Textual themes: `exofox`
  (dark, default) and `exofox-light`, including the scrollbar
  tokens (invisible track, stone thumb, gold under the hand).
- `composer.py` — `Composer`, a borderless multiline `TextArea`
  flush with the surface, and `ComposerBar`, the `❯`-guttered
  input line (glyph gold while focused) mounted by both the main
  screen and the ledger: Enter submits, Shift+Enter (or Ctrl+J
  where the terminal cannot report it) inserts a newline, Up/Down
  at an empty composer recall the submission history — one shared
  list (`app.composer_history`) across every composer.
- `status.py` — `StatusBar` and `StatusLine`: the instrument
  cluster. Identity (`◆ agent · model`), a braille spinner with
  elapsed time while the bound track works (amber during a tool
  call), per-track dots (gold = bound, spinner = hidden and
  streaming, teal = unseen completion, muted = idle), the action
  lane's last-failure marker, the conversation title and compact
  last-turn usage as whispers, and right-aligned key hints.
  Colors resolve through CSS component classes so any theme's
  `auto` shades work.
- `log_bridge.py` — console-handler takeover for the app's
  lifetime plus the forwarding handler that turns WARNING+ log
  records into toasts.
- `__init__.py` — re-exports `ClaiaApp`.

## How It Fits

`main()` builds the registry/settings, starts the workers, and
launches `ClaiaApp(registry=..., settings=...)` when stdin/stdout
is a TTY, no args were given, and `TERM` is not `dumb`; Textual is
imported only inside that branch. Workers stop in `main()` after
the app returns.

A chat submit runs `prepare_query_task` (the same helper the
one-shot query uses, given the track's conversation) and enqueues
the task. `TaskEvent` callbacks fire on worker threads: they feed
a `StreamRouter` and post the resulting block events into the app
tagged with their track (`post_message` is thread-safe). On the
UI thread the events pass through the track's `Pacer` before
reaching its live `TurnView` — the one app timer ticks every live
pacer, so hidden tracks keep streaming. Persistence stays in the
terminal callbacks on the worker thread, exactly as in
`QueryCommand`.

A `:` line becomes an `Action` on the serial lane: tokens after
the colon go to `Commands.run` untouched and the ledger opens to
show the record (already open: the record prepends live) — except
for quiet-listed commands (`conversation new`/`load`, `quit`)
whose payoff is the main screen. Failures also toast,
`Result.is_exit()` maps to `app.exit()`, and the switchboard
reconciles the bound track against `settings.active_conversation`
after every action — so `conversation new`/`load` rebind or
create tracks with no command interception. Commands whose
`Result` sets `format="markdown"` (`help`, `model list` so far)
render as markdown in the ledger and through rich in one-shot
mode. From the ledger's own composer, another `:` line runs in
place while plain text submits as chat and returns to the
transcript. `query` redirects to a chat submit; `setup` is
refused with a pointer to one-shot.

On launch (and when a load names a conversation with no track),
prior turns rebuild through `replay_turn` (from `..stream`) into
the same turn views, instantly and unpaced — live and reloaded
conversations render identically by construction, with
consecutive same-label assistant messages merging into one view.

Esc cancels the bound track's in-flight task
(`task.request_cancel()`); Alt+N/Alt+P hop tracks; Alt+A toggles
the ledger page; F1 (Alt+H alias) toggles the help card; Ctrl+Q
quits, with Alt+Q as the alias for terminals that capture Ctrl+Q,
and quit cancels every track's in-flight task first. Submitting
into a busy track queues exactly one pending message that
auto-submits when that track's turn ends.
