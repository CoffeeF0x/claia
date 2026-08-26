# CLI TUI

The interactive face of `claia.cli`: bare `claia` on a TTY opens
this full-screen Textual app. One track (the active conversation),
a composer that stays live during generation, paced turn-view
rendering with markdown, muted thinking, and tool blocks, all in
the ExoFox family-look theme. Tracks and the action lane are a
later phase.

## What Lives Here

- `app.py` — `ClaiaApp`: layout, bindings, task lifecycle, the
  worker→UI thread bridge, the pacer timer, history replay, and
  logging ownership.
- `transcript.py` — `Transcript`, a scrolling pane of user label
  blocks and `TurnView`s with follow-tail (Textual anchor)
  scrolling.
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
- `status.py` — `StatusBar`: model, agent, conversation, task
  state, the last turn's usage/duration, and right-aligned key
  hints (`^J newline · Esc cancel · ^Q quit`).
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

A submit runs `prepare_query_task` (the same helper the one-shot
query uses) and enqueues the task. `TaskEvent` callbacks fire on
worker threads: they feed a `StreamRouter` and post the resulting
block events into the app (`post_message` is thread-safe). On the
UI thread the events pass through the turn's `Pacer` before
reaching the live `TurnView`; tool results post as `ToolResult`
events when their artifact persists. Usage/duration goes from
`StreamEnd` to the status bar; persistence stays in the terminal
callbacks on the worker thread, exactly as in `QueryCommand`.

On launch, prior turns rebuild through `replay_turn` (from
`..stream`) into the same turn views, instantly and unpaced —
live and reloaded conversations render identically by
construction, with consecutive same-label assistant messages
merging into one view.

Esc cancels the in-flight task (`task.request_cancel()`); Ctrl+Q
quits, with Alt+Q as the alias for terminals that capture Ctrl+Q;
quit requests cancel first when a task is in flight. Submitting
while busy queues exactly one pending message that auto-submits
when the turn ends.
