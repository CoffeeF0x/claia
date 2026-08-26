# claia.cli tests

Tests for the CLI application layer.

- `test_stream_router.py` — golden tests: chunk sequences in,
  block-event sequences out (split tags, NATIVE/MANUAL tool calls,
  think spans, parse errors as metadata).
- `test_block_renderer.py` — block events in, terminal output out
  (default/verbose, TTY/piped, `NO_COLOR`).
- `test_dispatch.py` — the args / TTY / piped-stdin invocation
  matrix and result-to-exit-code mapping.
- `test_lazy_conversation.py` — conversation commands avoid
  allocating conversations they don't need.
