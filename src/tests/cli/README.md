# claia.cli tests

Tests for the CLI application layer.

- `test_stream_router.py` — golden tests: chunk sequences in,
  block-event sequences out (split tags, NATIVE/MANUAL tool calls,
  think spans, parse errors as metadata).
- `test_stream_replay.py` — golden tests: persisted messages and
  utilities in, the live-equivalent block-event sequences out
  (thinking spans, MANUAL/NATIVE calls with results, notices,
  router parity).
- `test_block_renderer.py` — block events in, terminal output out
  (default/verbose, TTY/piped, `NO_COLOR`).
- `test_tui_pacer.py` — drip ordering, structural barriers,
  end-drain acceleration, instant cancel/failure flush.
- `test_tui_app.py` — headless TUI runs with the dummy model:
  turn flow, thinking/tool segments, reload identity, queueing,
  cancel, follow-tail, toasts.
- `test_dispatch.py` — the args / TTY / piped-stdin invocation
  matrix and result-to-exit-code mapping.
- `test_lazy_conversation.py` — conversation commands avoid
  allocating conversations they don't need.
