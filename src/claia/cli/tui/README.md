# CLI TUI

The interactive face of `claia.cli`: bare `claia` on a TTY opens
this full-screen Textual app. One track (the active conversation),
a composer that stays live during generation, a streamed
plain-text tail, and a status bar. Plain rendering is deliberate —
turn widgets, markdown, and the theme are later phases.

## What Lives Here

- `app.py` — `ClaiaApp`: layout, bindings, task lifecycle, the
  worker→UI thread bridge, and logging ownership.
- `transcript.py` — `Transcript`, a scrolling pane of role-labelled
  plain-text blocks with follow-tail (Textual anchor) scrolling.
- `composer.py` — `Composer`, a multiline `TextArea`: Enter
  submits, Shift+Enter (or Ctrl+J where the terminal cannot report
  it) inserts a newline, Up/Down at an empty composer recall the
  in-session submission history.
- `status.py` — `StatusBar`: model, agent, conversation, task
  state, and the last turn's usage/duration.
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
block events into the app (`post_message` is thread-safe); the UI
thread renders TEXT deltas live, drops THINKING, shows tool calls
as one dim `[tool <name>]` line and artifacts as
`[saved: <name>]`, and routes usage/duration from `StreamEnd` to
the status bar. Persistence stays in the terminal callbacks on the
worker thread, exactly as in `QueryCommand`.

Esc cancels the in-flight task (`task.request_cancel()`); quit
(Textual's default `ctrl+q`) requests cancel first when a task is
in flight. Submitting while busy queues exactly one pending
message that auto-submits when the turn ends.
