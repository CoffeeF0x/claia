"""
Stream router: task output in, semantic block events out.

Pure display-side logic. The router mirror-parses ``TextChunk``
content with the same ``TagSpec`` list the agent uses (identical
segmentation), normalizes NATIVE ``ToolChunk``s and MANUAL tool
tags into one ``ToolCall`` shape, and collects usage/metrics for
the terminal ``StreamEnd``. It never prints and never dispatches
tools — the agent layer already did that.

Wire it to a task's callbacks:

    router = StreamRouter(resolve_tag_specs(model_def))
    task.on(TaskEvent.CHUNK, lambda c: handle(router.feed(c)))
    task.on(TaskEvent.ARTIFACT, lambda a, _: handle(router.feed_artifact(a)))
    # on COMPLETE / ERROR / CANCELLED:
    handle(router.end(status, error=...))
"""

# External dependencies
import json
from typing import Any, Iterable, Iterator, List, Optional

# Internal dependencies
from ...core.data.chunks import MetricsChunk, TextChunk, ToolChunk, UsageChunk
from ...core.enums.parser import TagType
from ...core.enums.task import TaskStatus
from ...core.parser import (
  DEFAULT_TAGS,
  ParseError,
  ParseEvent,
  TagEvent,
  TagParser,
  TagSpec,
  TextEvent,
)
from ...core.tools.protocols.simple.payload import decode_payload
from .blocks import (
  ArtifactNotice,
  BlockEvent,
  Channel,
  StreamEnd,
  TextDelta,
  ToolCall,
  ToolSource,
)



########################################################################
#                              FUNCTIONS                               #
########################################################################
def manual_tool_name(attributes, content: str) -> str:
  """Resolve a MANUAL tool call's name the way the agent does.

  Tag attribute first, then the payload's ``"name"`` field; empty
  string when neither yields one. Shared with replay so persisted
  TOOL utilities resolve identically.
  """
  name = (attributes.get("name") or "").strip() if attributes else ""
  if not name:
    try:
      _params, hint = decode_payload(content)
      name = (hint or "").strip()
    except ValueError:
      name = ""
  return name



########################################################################
#                             STREAM ROUTER                            #
########################################################################
class StreamRouter:
  """Per-task translator from chunks/artifacts to block events.

  Construct with the ``TagSpec`` list resolved for the task's model
  (``resolve_tag_specs(model_def)``); defaults to ``DEFAULT_TAGS``
  when none is given.
  """

  def __init__(self, tag_specs: Optional[Iterable[TagSpec]] = None):
    specs = list(tag_specs) if tag_specs is not None else list(DEFAULT_TAGS.values())
    self._parser = TagParser(specs)
    self._emitted = 0  # buffer index up to which TEXT has been emitted
    self._usage: Optional[UsageChunk] = None
    self._metrics: Optional[MetricsChunk] = None
    self._parse_errors: List[ParseError] = []

  # ------------------------------------------------------------------
  # Inputs
  # ------------------------------------------------------------------
  def feed(self, chunk: Any) -> Iterator[BlockEvent]:
    """Consume one ``TaskEvent.CHUNK`` payload; yield block events.

    Usage and metrics chunks are collected silently and surface on
    the ``StreamEnd`` from :meth:`end`. Chunk types with no text
    representation (image/audio/raw) yield nothing — their durable
    form arrives as an ``ARTIFACT`` notice from the agent.
    """
    if isinstance(chunk, ToolChunk):
      yield self._native_tool(chunk)
    elif isinstance(chunk, UsageChunk):
      self._usage = chunk
    elif isinstance(chunk, MetricsChunk):
      self._metrics = chunk
    elif isinstance(chunk, TextChunk):
      text = chunk.data if isinstance(chunk.data, str) else str(chunk.data or "")
      for ev in self._parser.feed(text):
        yield from self._handle_parse_event(ev)
      yield from self._pending_plain_text()

  def feed_artifact(self, artifact: Any) -> Iterator[BlockEvent]:
    """Consume one ``TaskEvent.ARTIFACT`` payload."""
    yield ArtifactNotice(name=getattr(artifact, "name", "") or "artifact")

  def end(
    self,
    status: TaskStatus,
    error: Optional[str] = None,
  ) -> Iterator[BlockEvent]:
    """Terminal task event: flush the parser, then yield ``StreamEnd``."""
    for ev in self._parser.flush():
      yield from self._handle_parse_event(ev)
    yield StreamEnd(
      status=status,
      error=error,
      usage=self._usage,
      metrics=self._metrics,
      parse_errors=tuple(self._parse_errors),
    )

  # ------------------------------------------------------------------
  # Parse-event handling
  # ------------------------------------------------------------------
  def _handle_parse_event(self, ev: ParseEvent) -> Iterator[BlockEvent]:
    if isinstance(ev, TextEvent):
      # The scan-state reads below may have emitted part of this
      # span already; the watermark keeps the two sources disjoint.
      delta = ev.text[max(0, self._emitted - ev.start_index):]
      self._emitted = max(self._emitted, ev.end_index)
      if delta:
        yield TextDelta(text=delta, channel=Channel.TEXT)
    elif isinstance(ev, TagEvent):
      self._emitted = max(self._emitted, ev.end_index)
      if ev.tag_type is TagType.TOOL:
        yield self._manual_tool(ev)
      elif ev.tag_type is TagType.THINKING:
        if ev.content:
          yield TextDelta(text=ev.content, channel=Channel.THINKING)
      elif ev.content:
        # Other tag spans (e.g. REFERENCE) render as plain content;
        # the delimiters never hit the screen.
        yield TextDelta(text=ev.content, channel=Channel.TEXT)
    elif isinstance(ev, ParseError):
      self._parse_errors.append(ev)

  def _pending_plain_text(self) -> Iterator[BlockEvent]:
    # TextEvents only arrive at tag boundaries (or flush) — too late
    # for live display. confirmed_text exposes what the scanner has
    # ruled out as tag material so it can render immediately.
    text, self._emitted = self._parser.confirmed_text(self._emitted)
    if text:
      yield TextDelta(text=text, channel=Channel.TEXT)

  # ------------------------------------------------------------------
  # Tool-call normalization
  # ------------------------------------------------------------------
  @staticmethod
  def _native_tool(chunk: ToolChunk) -> ToolCall:
    args = chunk.payload if chunk.payload is not None else chunk.data
    if not isinstance(args, str):
      try:
        args = json.dumps(args)
      except (TypeError, ValueError):
        args = str(args)
    return ToolCall(
      name=(chunk.tool_name or "").strip(),
      args=args or "",
      call_id=chunk.call_id,
      source=ToolSource.NATIVE,
    )

  @staticmethod
  def _manual_tool(ev: TagEvent) -> ToolCall:
    return ToolCall(
      name=manual_tool_name(ev.attributes, ev.content),
      args=ev.content,
      call_id=None,
      source=ToolSource.MANUAL,
    )
