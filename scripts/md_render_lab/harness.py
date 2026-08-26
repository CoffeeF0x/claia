"""
Shared lab bits for the markdown-streaming comparison demos.

Run a demo from the repo root:

  python scripts/md_render_lab/demo_1_mdstream.py

``import harness`` works because the script directory is on
sys.path. Disposable — not part of the package.
"""

# External dependencies
import asyncio
import random
import time
from contextlib import suppress

from markdown_it import MarkdownIt
from rich.markdown import Markdown as RichMarkdown
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Footer, Static


########################################################################
#                              DOCUMENT                                #
########################################################################
DOCUMENT = """\
# Streaming sanity check

This paragraph streams in first. It mixes **bold**, *italic*,
`inline code`, and a [link](https://example.com) so partial
inline markup flashes by mid-parse before the tail settles.

## A list, because agents love lists

- First point, short and plain
- Second point with `code` and **weight**
  - A nested child to test indent handling
  - Another, with a longer sentence that will wrap when your
    terminal is narrow enough to force the issue
- Third point arrives after the nesting

## Code fence (the hard case)

Watch this one closely while the fence is *open* — the tail block
re-parses on every write until the closing backticks land:

```python
def stream_turn(chunks):
  \"\"\"Feed a parser one fragment at a time.\"\"\"
  buffer = []
  for chunk in chunks:
    buffer.append(chunk)
    if chunk.endswith("\\n"):
      yield "".join(buffer)
      buffer.clear()
  if buffer:
    yield "".join(buffer)


for event in stream_turn(["hel", "lo\\n", "wor", "ld"]):
  print(event, end="")
```

## A table

| Route  | Wire form        | Downstream       |
| ------ | ---------------- | ---------------- |
| NATIVE | `ToolChunk`      | one `ToolCall`   |
| MANUAL | `<tool …>` tags  | one `ToolCall`   |

> A blockquote for texture. Historical thinking will render like
> this someday — muted, part of the background.

## Numbered finish

1. The completed blocks above should never visibly re-render
2. Only this tail region should be doing work
3. When the stream ends, the whole document should look identical
   to a one-shot render of the same markdown

That is the whole test. Restart with `r`, flip delivery with `b`.
"""


########################################################################
#                          CHUNK PROFILES                              #
########################################################################
def tokens(text, lo=2, hi=18):
  """Split ``text`` into random-length fragments, LLM-token-ish."""
  rng = random.Random(7)
  pos = 0
  while pos < len(text):
    step = rng.randint(lo, hi)
    yield text[pos:pos + step]
    pos += step


def bursty(text):
  """(fragment, delay) pairs: token bursts between jittered stalls."""
  rng = random.Random(11)
  burst_left = 0
  for fragment in tokens(text):
    if burst_left <= 0:
      burst_left = rng.randint(3, 12)
      delay = 0.7 if rng.random() < 0.07 else rng.uniform(0.03, 0.25)
    else:
      delay = 0.0
    burst_left -= 1
    yield fragment, delay


def steady(text):
  """(fragment, delay) pairs: one small fragment every 25ms."""
  for fragment in tokens(text):
    yield fragment, 0.025


PROFILES = {"bursty": bursty, "steady": steady}


########################################################################
#                                PACER                                 #
########################################################################
class Pacer:
  """Async jitter buffer over a (fragment, delay) delivery source.

  ON: incoming fragments land in a backlog; a ~40ms tick re-emits
  smaller drips at a baseline ~80 chars/sec that scales up with
  backlog so the drain never lags far behind. End of stream dumps
  whatever is left. OFF: fragments pass through with their original
  delays. Same object in every demo so pacing is identical.
  """

  TICK = 0.04
  BASE_RATE = 80.0
  MAX_RATE = 480.0
  BACKLOG_GAIN = 2.0

  def __init__(self, source, enabled=True):
    self._source = source
    self._enabled = enabled

  def __aiter__(self):
    if self._enabled:
      return self._paced()
    return self._raw()

  async def _raw(self):
    for fragment, delay in self._source:
      if delay:
        await asyncio.sleep(delay)
      if fragment:
        yield fragment

  async def _paced(self):
    incoming = []
    done = False

    async def produce():
      nonlocal done
      try:
        for fragment, delay in self._source:
          if delay:
            await asyncio.sleep(delay)
          if fragment:
            incoming.append(fragment)
      finally:
        done = True

    task = asyncio.create_task(produce())
    backlog = ""
    next_tick = time.monotonic()
    try:
      while True:
        wait = next_tick - time.monotonic()
        if wait > 0:
          await asyncio.sleep(wait)
        else:
          await asyncio.sleep(0)
        next_tick += self.TICK
        if incoming:
          backlog += "".join(incoming)
          incoming.clear()
        if not backlog:
          if done:
            return
          continue
        if done:
          yield backlog
          return
        n = self._drip_size(len(backlog))
        yield backlog[:n]
        backlog = backlog[n:]
    finally:
      task.cancel()
      with suppress(asyncio.CancelledError):
        await task

  def _drip_size(self, backlog_len):
    rate = self.BASE_RATE + backlog_len * self.BACKLOG_GAIN
    rate = min(self.MAX_RATE, max(self.BASE_RATE, rate))
    return max(1, min(backlog_len, int(rate * self.TICK)))


########################################################################
#                         BLOCK BOUNDARIES                             #
########################################################################
_MD = MarkdownIt("gfm-like")


def split_frozen_live(text):
  """Split ``text`` into completed top-level blocks and a live tail.

  Uses markdown-it token ``map`` line ranges. The last top-level
  block is still open (including an unclosed fence, which is one
  fence token spanning to EOF). Everything before its start line
  is freezable. Returns ``(frozen_sources, live_tail)``.
  """
  if not text:
    return [], ""
  tokens = [
    tok for tok in _MD.parse(text)
    if tok.level == 0 and tok.map is not None and tok.nesting != -1
  ]
  if len(tokens) < 2:
    return [], text
  lines = text.splitlines(keepends=True)
  starts = [tok.map[0] for tok in tokens]
  live_at = starts[-1]
  frozen = [
    "".join(lines[starts[i]:starts[i + 1]])
    for i in range(len(starts) - 1)
  ]
  live = "".join(lines[live_at:])
  return frozen, live


def rich_markdown(source):
  return RichMarkdown(source)


def dim_text(source):
  return Text(source, style="dim")


########################################################################
#                                APP                                   #
########################################################################
class LabApp(App):
  """Shared chrome: status, follow-tail body, bindings, paced stream.

  Subclasses set ``STRATEGY`` and implement ``setup_run``,
  ``on_fragment``, and optionally ``on_stream_end`` /
  ``on_stream_close``.
  """

  STRATEGY = "?"
  TOTAL = len(DOCUMENT)

  BINDINGS = [
    ("b", "toggle_profile", "Bursty/steady"),
    ("p", "toggle_pacing", "Pace on/off"),
    ("r", "restart", "Restart"),
    ("q", "quit", "Quit"),
  ]

  CSS = """
  #status { dock: top; height: 1; padding: 0 1; background: $panel; }
  #body { height: 1fr; padding: 0 2; }
  #body > Static { width: 100%; height: auto; }
  """

  def __init__(self):
    super().__init__()
    self.profile = "bursty"
    self.pacing = True
    self.sent = 0
    self.started = 0.0
    self.finished = False

  def compose(self) -> ComposeResult:
    yield Static(id="status")
    yield VerticalScroll(id="body")
    yield Footer()

  def on_mount(self) -> None:
    self.query_one("#body", VerticalScroll).anchor()
    self.action_restart()

  def action_toggle_profile(self) -> None:
    self.profile = (
      "steady" if self.profile == "bursty" else "bursty"
    )
    self.action_restart()

  def action_toggle_pacing(self) -> None:
    self.pacing = not self.pacing
    self.action_restart()

  def action_restart(self) -> None:
    self.stream_document()

  def refresh_status(self) -> None:
    elapsed = 0.0
    if self.started:
      elapsed = time.monotonic() - self.started
    pace = "pace on" if self.pacing else "pace off"
    line = (
      f"{self.STRATEGY} | {self.profile} | {pace} | "
      f"{self.sent}/{self.TOTAL} chars | {elapsed:.1f}s"
    )
    if self.finished:
      line += " | done"
    self.query_one("#status", Static).update(line)

  async def setup_run(self, body: VerticalScroll) -> None:
    raise NotImplementedError

  async def on_fragment(self, fragment: str) -> None:
    raise NotImplementedError

  async def on_stream_end(self) -> None:
    return

  async def on_stream_close(self) -> None:
    return

  @work(exclusive=True)
  async def stream_document(self) -> None:
    body = self.query_one("#body", VerticalScroll)
    self.sent = 0
    self.finished = False
    self.started = time.monotonic()
    await body.remove_children()
    self.refresh_status()
    try:
      await self.setup_run(body)
      source = PROFILES[self.profile](DOCUMENT)
      async for fragment in Pacer(source, enabled=self.pacing):
        await self.on_fragment(fragment)
        self.sent += len(fragment)
        self.refresh_status()
      await self.on_stream_end()
      self.finished = True
      self.refresh_status()
    finally:
      await self.on_stream_close()
