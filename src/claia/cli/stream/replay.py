"""
Replay: persisted turns back into block events.

A pure function beside the router: one assistant message plus its
``UTILITY`` siblings in, the block-event sequence the router would
have emitted live out. Text is split around thinking/tool spans via
the utilities' source indices, MANUAL tool calls carry the persisted
tag payload, NATIVE calls (no indices) are unwrapped from the stored
envelope and placed after the text, and results come from the
``ToolArtifact``s attached to TOOL utilities. No UI imports.

Granularity differs from live streaming — each contiguous text run
is one ``TextDelta`` — but the joined text per channel and the event
order match, so a turn view renders both identically.
"""

# External dependencies
import json
from typing import Iterable, List, Optional

# Internal dependencies
from ...core.data.artifacts import TextArtifact
from ...core.data.models.conversation.message import Message
from ...core.enums.parser import TagType
from .blocks import (
  ArtifactNotice,
  BlockEvent,
  Channel,
  TextDelta,
  ToolCall,
  ToolResult,
  ToolSource,
)
from .router import manual_tool_name



########################################################################
#                              FUNCTIONS                               #
########################################################################
def replay_turn(
  message: Message,
  utilities: Iterable[Message],
) -> List[BlockEvent]:
  """Rebuild one assistant turn's block events from persisted data.

  ``utilities`` are the UTILITY siblings whose ``source_message_id``
  is this message (thread order). No ``StreamEnd`` is produced —
  status and accounting are not persisted per message.
  """
  source = message.content or ""
  spans = sorted(
    (u for u in utilities if _has_indices(u)),
    key=lambda u: u.start_index,
  )
  native = [
    u for u in utilities
    if not _has_indices(u) and u.tag_type is TagType.TOOL
  ]

  events: List[BlockEvent] = []
  pos = 0
  for utility in spans:
    _append_text(events, source[pos:utility.start_index])
    pos = max(pos, utility.end_index)
    content = utility.content or ""
    if utility.tag_type is TagType.TOOL:
      events.append(ToolCall(
        name=manual_tool_name(utility.attributes, content),
        args=content,
        call_id=None,
        source=ToolSource.MANUAL,
      ))
      events.extend(_results(utility))
    elif utility.tag_type is TagType.THINKING:
      if content:
        events.append(TextDelta(text=content, channel=Channel.THINKING))
    elif content:
      # Other tag spans (e.g. REFERENCE) render as plain content.
      events.append(TextDelta(text=content, channel=Channel.TEXT))
  _append_text(events, source[pos:])

  for utility in native:
    events.append(_native_call(utility))
    events.extend(_results(utility))

  # The primary text artifact is the message body (first TextArtifact,
  # per the Message contract); every other artifact gets a notice.
  primary = next(
    (a for a in message.artifacts if isinstance(a, TextArtifact)), None,
  )
  for artifact in message.artifacts:
    if artifact is primary:
      continue
    events.append(
      ArtifactNotice(name=getattr(artifact, "name", "") or "artifact")
    )
  return events



########################################################################
#                              INTERNALS                               #
########################################################################
def _has_indices(utility: Message) -> bool:
  return (
    utility.start_index is not None and utility.end_index is not None
  )


def _append_text(events: List[BlockEvent], text: str) -> None:
  if text:
    events.append(TextDelta(text=text, channel=Channel.TEXT))


def _results(utility: Message) -> List[ToolResult]:
  return [
    ToolResult(
      name=artifact.tool_name,
      body=artifact.payload_text(),
      call_id=artifact.call_id,
    )
    for artifact in utility.tool_result_artifacts()
  ]


def _native_call(utility: Message) -> ToolCall:
  """Unwrap a NATIVE utility's stored envelope back to router shape."""
  content = utility.content or ""
  name = ""
  args = content
  try:
    envelope = json.loads(content)
  except ValueError:
    envelope = None
  if isinstance(envelope, dict) and "parameters" in envelope:
    name = (envelope.get("name") or "").strip()
    try:
      args = json.dumps(envelope.get("parameters"))
    except (TypeError, ValueError):
      args = str(envelope.get("parameters"))
  return ToolCall(
    name=name,
    args=args,
    call_id=_first_call_id(utility),
    source=ToolSource.NATIVE,
  )


def _first_call_id(utility: Message) -> Optional[str]:
  for artifact in utility.tool_result_artifacts():
    if artifact.call_id:
      return artifact.call_id
  return None
