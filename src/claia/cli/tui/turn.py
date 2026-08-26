"""
Turn widgets: one ``TurnView`` per assistant turn.

A TurnView consumes block events and composes widgets in stream
order: markdown segments for TEXT (via ``Markdown.get_stream`` so
bursts collapse into few updates), muted plain-text segments for
THINKING (inline, never collapsed), ``ToolBlock``s for tool calls,
and dim notice lines for artifacts and terminal states. Live and
replayed turns run through the same :meth:`handle` pipeline — the
only difference is whether a pacer sits upstream — so both render
identically by construction.
"""

# External dependencies
import json
from typing import Iterable, List, Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Collapsible, Markdown, Static
from textual.widgets._markdown import MarkdownStream

# Internal dependencies
from ...core.enums.task import TaskStatus
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
#                              TOOL BLOCK                              #
########################################################################
class ToolBlock(Collapsible):
  """A dispatched tool call: gold-guttered, name line always visible.

  Collapsed (default) shows truncated pretty-printed args and a
  one-line result preview when a result exists; expanding swaps the
  previews for the full payloads. Results attach when they arrive —
  no placeholder while they don't.
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
    &.-collapsed > .tool-preview {
      display: block;
    }
    & > Contents {
      padding: 0 3;
    }
    & .tool-result {
      margin-top: 1;
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

  def compose(self) -> ComposeResult:
    yield self._title
    yield Static(
      Text(truncate(
        self.args_text, ARGS_PREVIEW_LINES, ARGS_PREVIEW_CHARS,
      )),
      classes="tool-preview tool-args-preview",
    )
    if self.result_body is not None:
      yield self._result_preview()
    with self.Contents():
      yield Static(Text(self.args_text), classes="tool-args")
      if self.result_body is not None:
        yield self._result_full()

  @property
  def has_result(self) -> bool:
    return self.result_body is not None

  def set_result(self, body: str) -> None:
    """Attach a result; mounts the preview/detail when already live."""
    self.result_body = body
    if self.is_mounted:
      self.mount(
        self._result_preview(),
        after=self.query_one(".tool-args-preview"),
      )
      self.query_one(Collapsible.Contents).mount(self._result_full())

  def _result_preview(self) -> Static:
    line = (self.result_body or "").strip().splitlines() or [""]
    return Static(
      Text("→ " + truncate(line[0], 1, RESULT_PREVIEW_CHARS)),
      classes="tool-preview tool-result-preview",
    )

  def _result_full(self) -> Static:
    return Static(Text(self.result_body or ""), classes="tool-result")



########################################################################
#                              TURN VIEW                               #
########################################################################
class TurnView(Vertical):
  """One assistant turn built from (optionally paced) block events."""

  DEFAULT_CSS = """
  TurnView {
    height: auto;
    margin-top: 1;

    & > .turn-label {
      color: $primary;
      text-style: bold;
    }
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
    self._markdown: Optional[Markdown] = None
    self._stream: Optional[MarkdownStream] = None
    self._thinking: Optional[Static] = None
    self._thinking_text = ""
    self._tools: List[ToolBlock] = []

  def compose(self) -> ComposeResult:
    yield Static(Text(self.label), classes="turn-label")

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
      self._notice(f"[saved: {event.name}]")
    elif isinstance(event, StreamEnd):
      await self.finish()
      if event.status is TaskStatus.CANCELLED:
        self._notice("[cancelled]", "notice-warning")
      if event.error:
        self._notice(f"[error: {event.error}]", "notice-error")

  async def load(self, events: Iterable[BlockEvent]) -> None:
    """Render a replayed turn: same pipeline, instant, unpaced."""
    for event in events:
      await self.handle(event)
    await self.finish()

  async def finish(self) -> None:
    """Stop the live stream and close all open segments."""
    await self._close_segments()

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
