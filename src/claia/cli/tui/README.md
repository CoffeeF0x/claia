# CLI TUI

The interactive face of `claia.cli`: bare `claia` on a TTY opens
this full-screen Textual app. Conversations are tracks owned by a
switchboard — every track keeps accumulating (paced turn views,
one queued message) whether or not it is on screen — with a live
composer that routes chat into the bound track and `:` lines onto
a serial action lane, all in the ExoFox family-look theme.

## What Lives Here

- `app.py` — `ClaiaApp`: layout, bindings, composer routing
  (`:` → action, else chat), the worker→UI thread bridge, the one
  pacer timer, action-lane outcomes (exit / toast / reconcile),
  and logging ownership.
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
- `panel.py` — `ActionPanel`, the toggleable newest-first record
  of every action (status glyph, command, full output) overlaid
  on the right edge, and `ActionRecord`.
- `transcript.py` — `Transcript`, a scrolling pane of user label
  blocks and `TurnView`s with follow-tail (Textual anchor)
  scrolling; one per track.
- `turn.py` — `TurnView` (one per assistant turn: markdown
  segments via `Markdown.get_stream`, inline muted thinking,
  notice lines) and `ToolBlock` (gold-guttered `Collapsible`:
  name line, truncated args preview, result preview, full
  payloads behind the toggle).
- `pacer.py` — `Pacer`, the per-turn jitter buffer: text drips
  at an adaptive rate on a ~40ms tick; structural events are
  barriers; graceful ends accelerate the drain, cancel/failure
  flushes instantly. Pure logic, no Textual imports.
- `theme.py` — the ExoFox palette as Textual themes: `exofox`
  (dark, default) and `exofox-light`.
- `composer.py` — `Composer`, a multiline `TextArea`: Enter
  submits, Shift+Enter (or Ctrl+J where the terminal cannot report
  it) inserts a newline, Up/Down at an empty composer recall the
  in-session submission history.
- `status.py` — `StatusBar`: model, agent, conversation,
  `track i/N`, task state, unseen badge (`●2`), the last turn's
  usage/duration, the action lane's last-failure marker, and
  right-aligned key hints.
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
the colon go to `Commands.run` untouched, the `Result` lands in
the action panel (failures also toast), `Result.is_exit()` maps
to `app.exit()`, and the switchboard reconciles the bound track
against `settings.active_conversation` after every action — so
`conversation new`/`load` rebind or create tracks with no command
interception. `query` redirects to a chat submit; `setup` is
refused with a pointer to one-shot; `actions` toggles the panel
(the key-free fallback for terminals that never deliver Alt+A).

On launch (and when a load names a conversation with no track),
prior turns rebuild through `replay_turn` (from `..stream`) into
the same turn views, instantly and unpaced — live and reloaded
conversations render identically by construction, with
consecutive same-label assistant messages merging into one view.

Esc cancels the bound track's in-flight task
(`task.request_cancel()`); Alt+N/Alt+P hop tracks; Alt+A toggles
the action panel; Ctrl+Q quits, with Alt+Q as the alias for
terminals that capture Ctrl+Q, and quit cancels every track's
in-flight task first. Submitting into a busy track queues exactly
one pending message that auto-submits when that track's turn ends.
