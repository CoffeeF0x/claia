"""
Semantic block events produced by the stream router.

These are the display-side vocabulary: renderers consume block
events instead of raw chunks, so NATIVE tool calls (``ToolChunk``)
and MANUAL tool tags look identical downstream, and thinking spans
are separated from assistant text by channel instead of by raw tag
delimiters.
"""

# External dependencies
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple, Union

# Internal dependencies
from ...core.data.chunks import MetricsChunk, UsageChunk
from ...core.enums.task import TaskStatus
from ...core.parser import ParseError



########################################################################
#                                ENUMS                                 #
########################################################################
class Channel(Enum):
  """Which stream a text delta belongs to."""
  TEXT = "text"
  THINKING = "thinking"


class ToolSource(Enum):
  """How a tool call arrived: a native ToolChunk or a parsed tag."""
  NATIVE = "native"
  MANUAL = "manual"



########################################################################
#                             BLOCK EVENTS                             #
########################################################################
@dataclass(frozen=True)
class TextDelta:
  """A span of streamed text on the TEXT or THINKING channel."""
  text: str
  channel: Channel = Channel.TEXT


@dataclass(frozen=True)
class ToolCall:
  """A tool call the agent layer dispatched (or will refuse).

  Purely informational — the router never executes tools. ``name``
  is empty when the call is nameless/malformed; ``args`` is the raw
  argument payload (tag content or JSON-encoded chunk payload).
  """
  name: str
  args: str = ""
  call_id: Optional[str] = None
  source: ToolSource = ToolSource.MANUAL


@dataclass(frozen=True)
class ArtifactNotice:
  """An artifact was attached to the turn (tool result, image, …)."""
  name: str


@dataclass(frozen=True)
class StreamEnd:
  """Terminal event: task status plus collected accounting.

  ``parse_errors`` carries any ``ParseError`` events from the mirror
  parser as metadata — they are never rendered as content.
  """
  status: TaskStatus
  error: Optional[str] = None
  usage: Optional[UsageChunk] = None
  metrics: Optional[MetricsChunk] = None
  parse_errors: Tuple[ParseError, ...] = field(default_factory=tuple)


BlockEvent = Union[TextDelta, ToolCall, ArtifactNotice, StreamEnd]
