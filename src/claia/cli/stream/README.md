# CLI Stream

Display-side stream routing: task output in, semantic block events
out. This package owns the translation from raw chunks/artifacts to
a renderer-friendly vocabulary; it never prints and never dispatches
tools (the agent layer already did that).

## What Lives Here

- `blocks.py` — the block-event dataclasses: `TextDelta` (with a
  `Channel` of TEXT or THINKING), `ToolCall` (normalized from both
  sources, tagged with `ToolSource`), `ToolResult`,
  `ArtifactNotice`, and `StreamEnd` (terminal status plus
  usage/metrics/parse errors).
- `router.py` — `StreamRouter`, the per-task translator.
- `replay.py` — `replay_turn`, the router's mirror for persisted
  data: one assistant message plus its `UTILITY` siblings back
  into the block events the router would have emitted live.
- `__init__.py` — re-exports the public names.

## How It Fits

`StreamRouter` mirror-parses `TextChunk` content with a `TagParser`
built from the same `TagSpec` list the agent uses
(`resolve_tag_specs(model_def)`), so display segmentation always
matches agent segmentation. NATIVE `ToolChunk`s and MANUAL
`[TOOL_CALL]` tag spans collapse into the one `ToolCall` shape;
think spans become THINKING-channel deltas; usage/metrics chunks
are collected silently and surface on the final `StreamEnd`.

Wire it to a task's callbacks and hand the events to a renderer:

```python
from claia.cli.stream import StreamRouter
from claia.core.enums.task import TaskEvent, TaskStatus
from claia.core.parser import resolve_tag_specs

router = StreamRouter(resolve_tag_specs(model_def))
task.on(TaskEvent.CHUNK, lambda c: handle(router.feed(c)))
task.on(TaskEvent.ARTIFACT, lambda a, _: handle(router.feed_artifact(a)))
# on COMPLETE / ERROR / CANCELLED:
handle(router.end(TaskStatus.COMPLETED))
```

`QueryCommand` renders the events as plaintext; the TUI feeds the
same events through a display pacer into turn-view widgets, and
uses `replay_turn` to rebuild persisted turns as the identical
event sequence.
