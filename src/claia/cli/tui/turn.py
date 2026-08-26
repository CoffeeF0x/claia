"""
Turn widgets: one ``TurnView`` per assistant turn.

A TurnView opens with a ``TurnLabel`` heading (gold glyph + name, a
hairline rule, the turn's compact usage whispered at the end once a
live turn closes), then consumes block events and composes widgets
in stream order: markdown segments for TEXT (via
``Markdown.get_stream`` so bursts collapse into few updates), muted
plain-text segments for THINKING (inline, never collapsed),
``ToolBlock``s for tool calls (breathing gold until their result
lands), and dim notice lines for artifacts and terminal states.
Live and replayed turns run through the same :meth:`handle`
pipeline — the only difference is whether a pacer sits upstream —
so both render identically by construction.
"""

# External dependencies
import json
import math
from typing import Iterable, List, Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.timer import Timer
from textual.widget import Widget
from textual.widgets import Collapsible, Markdown, Static
from textual.widgets._markdown import MarkdownStream

# Internal dependencies
from ...core.enums.task import TaskStatus
from ..renderer import compact_summary
from ..stream import (
  ArtifactNotice,
  BlockEvent,
  Channel,
  StreamEnd,
  TextDelta,
  ToolCall,
  ToolResult,
)



########################################################################
#                              CONSTANTS                               #
########################################################################
ARGS_PREVIEW_LINES = 3
ARGS_PREVIEW_CHARS = 240
RESULT_PREVIEW_CHARS = 120

PULSE_TICK = 0.1     # seconds between breathing frames
PULSE_STEP = 0.4     # phase advance per frame (radians)



########################################################################
#                              FUNCTIONS                               #
########################################################################
def pretty_args(args: str) -> str:
  """Pretty-print a tool payload; non-JSON payloads pass through.

  The MANUAL envelope (``{"name": …, "parameters": …}``) unwraps to
  its parameters — the name is already on the block's title line —
  so MANUAL and NATIVE calls display identically.
  """
  try:
    payload = json.loads(args)
  except (TypeError, ValueError):
    return args or ""
  if isinstance(payload, dict) and "parameters" in payload:
    payload = payload.get("parameters")
  try:
    return json.dumps(payload, indent=2)
  except (TypeError, ValueError):
    return str(payload)


def truncate(text: str, max_lines: int, max_chars: int) -> str:
  """Clip ``text`` for a preview, appending an ellipsis when cut."""
  clipped = text[:max_chars]
  lines = clipped.splitlines() or [""]
  if len(lines) > max_lines:
    clipped = "\n".join(lines[:max_lines])
  if clipped != text:
    clipped = clipped.rstrip() + " …"
  return clipped



########################################################################
#                              TURN LABEL                              #
########################################################################
class TurnLabel(Widget):
  """A turn's heading: glyph + name, a hairline rule, trailing meta.

  The rule stretches to the widget's width; ``meta`` (the turn's
  compact usage/duration, live turns only — accounting is not
  persisted per message) whispers at the right end once the turn
  closes.
  """

  COMPONENT_CLASSES = {
    "turnlabel--name",
    "turnlabel--rule",
    "turnlabel--meta",
  }

  DEFAULT_CSS = """
  TurnLabel {
    height: 1;
  }
  TurnLabel > .turnlabel--name {
    color: $primary;
    text-style: bold;
  }
  TurnLabel > .turnlabel--rule {
    color: $text-muted 35%;
  }
  TurnLabel > .turnlabel--meta {
    color: $text-muted;
  }
  """

  def __init__(self, label: str, **kwargs):
    super().__init__(**kwargs)
    self.label = label
    self.meta: Optional[str] = None

  def set_meta(self, meta: str) -> None:
    self.meta = meta
    self.refresh()

  def render(self) -> Text:
    name = self.get_component_rich_style("turnlabel--name")
    rule = self.get_component_rich_style("turnlabel--rule")
    meta_style = self.get_component_rich_style("turnlabel--meta")
    meta = f" {self.meta}" if self.meta else ""
    text = Text(no_wrap=True, overflow="crop")
    text.append("◆ ", name)
    text.append(self.label, name)
    fill = self.size.width - len(self.label) - len(meta) - 3
    if fill > 1:
      text.append(" " + "╌" * fill, rule)
    if meta:
      text.append(meta, meta_style)
    return text



########################################################################
#                              TOOL BLOCK                              #
########################################################################
class ToolBlock(Collapsible):
  """A dispatched tool call: gold-guttered, name line always visible.

  Collapsed (default) shows truncated pretty-printed args and a
  one-line result preview when a result exists; expanding swaps the
  previews for the full payloads. Results attach when they arrive —
  no placeholder, but the gold name line breathes (a text-opacity
  pulse on its own timer) until the result lands or the turn ends.
  """

  DEFAULT_CSS = """
  ToolBlock {
    height: auto;
    margin: 1 0;
    padding: 0;
    background: transparent;
    border-top: none;
    border-left: outer $primary;

    & > CollapsibleTitle {
      padding: 0 1;
      color: $primary;
      text-style: bold;
    }
    & > .tool-preview {
      display: none;
      padding: 0 3;
      color: $text-muted;
    }
    &.-collapsed > .tool-args-preview {
      display: block;
    }
    &.-collapsed.-has-result > .tool-result-preview {
      display: block;
    }
    & > Contents {
      padding: 0 3;
    }
    & .tool-result {
      display: none;
      margin-top: 1;
    }
    &.-has-result .tool-result {
      display: block;
    }
  }
  """

  def __init__(self, name: str, args: str, **kwargs):
    super().__init__(
      title=name or "unknown",
      collapsed=True,
      **kwargs,
    )
    self.tool_name = name or "unknown"
    self.args_text = pretty_args(args)
    self.result_body: Optional[str] = None
    self._settled = False
    self._pulse_timer: Optional[Timer] = None
    self._pulse_phase = 0
    self._result_preview: Optional[Static] = None
    self._result_full: Optional[Static] = None

  def on_mount(self) -> None:
    animated = getattr(self.app, "animation_level", "full") != "none"
    if self.result_body is None and not self._settled and animated:
      self._pulse_timer = self.set_interval(PULSE_TICK, self._pulse)

  def compose(self) -> ComposeResult:
    # The result widgets always compose (hidden behind ``-has-result``)
    # and render from current state, so a result that lands at any
    # point relative to mounting — same pacer tick, mid-mount, or
    # replay — displays identically. Nothing mounts later.
    yield self._title
    yield Static(
      Text(truncate(
        self.args_text, ARGS_PREVIEW_LINES, ARGS_PREVIEW_CHARS,
      )),
      classes="tool-preview tool-args-preview",
    )
    self._result_preview = Static(
      self._preview_text(), classes="tool-preview tool-result-preview",
    )
    yield self._result_preview
    with self.Contents():
      yield Static(Text(self.args_text), classes="tool-args")
      self._result_full = Static(
        Text(self.result_body or ""), classes="tool-result",
      )
      yield self._result_full

  @property
  def has_result(self) -> bool:
    return self.result_body is not None

  def set_result(self, body: str) -> None:
    """Attach a result; the composed widgets re-render from state."""
    self.settle()
    self.result_body = body
    self.add_class("-has-result")
    if self._result_preview is not None:
      self._result_preview.update(self._preview_text())
    if self._result_full is not None:
      self._result_full.update(Text(body))

  def settle(self) -> None:
    """Stop breathing: a result arrived or the turn is over."""
    self._settled = True
    if self._pulse_timer is not None:
      self._pulse_timer.stop()
      self._pulse_timer = None
    self._title.styles.text_opacity = 1.0

  def _pulse(self) -> None:
    self._pulse_phase += 1
    wave = (math.sin(self._pulse_phase * PULSE_STEP) + 1) / 2
    self._title.styles.text_opacity = 0.45 + 0.55 * wave

  def _preview_text(self) -> Text:
    line = (self.result_body or "").strip().splitlines() or [""]
    return Text("→ " + truncate(line[0], 1, RESULT_PREVIEW_CHARS))



########################################################################
#                              TURN VIEW                               #
########################################################################
class TurnView(Vertical):
  """One assistant turn built from (optionally paced) block events."""

  DEFAULT_CSS = """
  TurnView {
    height: auto;
    margin-top: 1;

    & > Markdown {
      padding: 0;
      margin: 0;
      background: transparent;
    }
    & > .turn-thinking {
      color: $text-muted;
      text-style: italic;
    }
    & > .turn-notice {
      text-style: dim;
    }
    & > .notice-warning {
      color: $warning;
    }
    & > .notice-error {
      color: $error;
    }
  }
  """

  def __init__(self, label: str, **kwargs):
    super().__init__(**kwargs)
    self.label = (label or "").upper()
    self._heading = TurnLabel(self.label)
    self._markdown: Optional[Markdown] = None
    self._stream: Optional[MarkdownStream] = None
    self._thinking: Optional[Static] = None
    self._thinking_text = ""
    self._tools: List[ToolBlock] = []

  def compose(self) -> ComposeResult:
    yield self._heading

  # ── Event intake ─────────────────────────────────────────────────

  async def handle(self, event: BlockEvent) -> None:
    """Consume one block event; mutations stay on the UI thread."""
    if isinstance(event, TextDelta):
      if event.channel is Channel.THINKING:
        await self._close_markdown()
        self._append_thinking(event.text)
      else:
        self._close_thinking()
        await self._write_markdown(event.text)
    elif isinstance(event, ToolCall):
      await self._close_segments()
      block = ToolBlock(event.name, event.args)
      self._tools.append(block)
      self.mount(block)
    elif isinstance(event, ToolResult):
      self._attach_result(event)
    elif isinstance(event, ArtifactNotice):
      await self._close_segments()
      self._notice(f"— saved {event.name}")
    elif isinstance(event, StreamEnd):
      await self.finish()
      meta = compact_summary(event)
      if meta:
        self._heading.set_meta(meta)
      if event.status is TaskStatus.CANCELLED:
        self._notice("— cancelled", "notice-warning")
      if event.error:
        self._notice(
          f"— well, that wasn't supposed to happen: {event.error}",
          "notice-error",
        )

  async def load(self, events: Iterable[BlockEvent]) -> None:
    """Render a replayed turn: same pipeline, instant, unpaced."""
    for event in events:
      await self.handle(event)
    await self.finish()

  async def finish(self) -> None:
    """Stop the live stream, close open segments, settle the tools."""
    await self._close_segments()
    for block in self._tools:
      block.settle()

  # ── Segments ─────────────────────────────────────────────────────

  async def _write_markdown(self, text: str) -> None:
    if self._markdown is None:
      self._markdown = Markdown(classes="turn-markdown")
      self.mount(self._markdown)
      self._stream = Markdown.get_stream(self._markdown)
    await self._stream.write(text)

  async def _close_markdown(self) -> None:
    if self._stream is not None:
      await self._stream.stop()
    self._stream = None
    self._markdown = None

  def _append_thinking(self, text: str) -> None:
    if self._thinking is None:
      self._thinking = Static(classes="turn-thinking")
      self._thinking_text = ""
      self.mount(self._thinking)
    self._thinking_text += text
    self._thinking.update(Text(self._thinking_text))

  def _close_thinking(self) -> None:
    self._thinking = None
    self._thinking_text = ""

  async def _close_segments(self) -> None:
    await self._close_markdown()
    self._close_thinking()

  # ── Tool results and notices ─────────────────────────────────────

  def _attach_result(self, event: ToolResult) -> None:
    # Calls dispatch serially in-stream, so a result belongs to the
    # most recent block still waiting for one.
    for block in reversed(self._tools):
      if not block.has_result:
        block.set_result(event.body)
        return

  def _notice(self, line: str, extra_class: str = "") -> None:
    classes = f"turn-notice {extra_class}".strip()
    self.mount(Static(Text(line), classes=classes))
