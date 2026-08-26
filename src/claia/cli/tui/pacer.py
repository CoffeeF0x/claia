"""
Display pacer: block events in, block events out, smoothed.

The same event vocabulary flows through both sides, so the turn view
cannot tell whether pacing is on — replay and tests can bypass the
pacer entirely. Pure logic with no Textual imports: the app drives
:meth:`tick` from a ~40ms timer.

TEXT and THINKING deltas buffer in arrival order and drip out at an
adaptive rate (a baseline that scales with backlog, ported from the
retired render lab). Structural events — ``ToolCall``,
``ToolResult``, ``ArtifactNotice``, ``StreamEnd`` — are barriers:
they emit only once the text queued before them has drained, so a
tool marker never appears before the sentence that led to it. A
graceful ``StreamEnd`` accelerates the drain; a CANCELLED/FAILED end
flushes everything immediately.
"""

# External dependencies
from typing import Iterable, List, Union

# Internal dependencies
from ...core.enums.task import TaskStatus
from ..stream import BlockEvent, Channel, StreamEnd, TextDelta



########################################################################
#                              CONSTANTS                               #
########################################################################
TICK = 0.04           # seconds between drips
BASE_RATE = 80.0      # chars/sec floor
BACKLOG_GAIN = 2.0    # extra chars/sec per buffered char
MAX_RATE = 480.0      # chars/sec ceiling while streaming
END_BOOST = 4.0       # rate and ceiling multiplier while end-draining

_INSTANT_STATUSES = (TaskStatus.CANCELLED, TaskStatus.FAILED)



########################################################################
#                               CLASSES                                #
########################################################################
class _TextRun:
  """A contiguous run of buffered text on one channel."""

  __slots__ = ("channel", "text")

  def __init__(self, channel: Channel, text: str):
    self.channel = channel
    self.text = text


class Pacer:
  """Per-turn jitter buffer between the router and the turn view.

  :meth:`feed` queues incoming events (returning any that must flush
  immediately); :meth:`tick` returns the next paced slice. ``done``
  turns True once the terminal ``StreamEnd`` has been emitted.
  """

  def __init__(self):
    self._queue: List[Union[_TextRun, BlockEvent]] = []
    self._ending = False
    self._instant = False
    self._done = False

  @property
  def done(self) -> bool:
    return self._done

  @property
  def pending(self) -> bool:
    return bool(self._queue)

  # ── Input ────────────────────────────────────────────────────────

  def feed(self, events: Iterable[BlockEvent]) -> List[BlockEvent]:
    """Queue events; returns an immediate flush on cancel/failure."""
    for event in events:
      if isinstance(event, TextDelta):
        last = self._queue[-1] if self._queue else None
        if isinstance(last, _TextRun) and last.channel is event.channel:
          last.text += event.text
        elif event.text:
          self._queue.append(_TextRun(event.channel, event.text))
        continue
      self._queue.append(event)
      if isinstance(event, StreamEnd):
        self._ending = True
        if event.status in _INSTANT_STATUSES:
          self._instant = True
    if self._instant:
      return self._flush()
    return []

  # ── Output ───────────────────────────────────────────────────────

  def tick(self) -> List[BlockEvent]:
    """Return the next paced slice of events, in order."""
    if self._instant:
      return self._flush()
    out: List[BlockEvent] = []
    budget = self._budget()
    while self._queue:
      head = self._queue[0]
      if not isinstance(head, _TextRun):
        out.append(self._queue.pop(0))
        if isinstance(head, StreamEnd):
          self._done = True
        continue
      if budget <= 0:
        break
      take = min(budget, len(head.text))
      out.append(TextDelta(text=head.text[:take], channel=head.channel))
      head.text = head.text[take:]
      budget -= take
      if head.text:
        break
      self._queue.pop(0)
    return out

  # ── Internals ────────────────────────────────────────────────────

  def _budget(self) -> int:
    """Characters allowed this tick, from the adaptive rate."""
    backlog = sum(
      len(item.text) for item in self._queue
      if isinstance(item, _TextRun)
    )
    if not backlog:
      return 0
    rate = BASE_RATE + BACKLOG_GAIN * backlog
    ceiling = MAX_RATE
    if self._ending:
      rate *= END_BOOST
      ceiling *= END_BOOST
    return max(1, int(min(rate, ceiling) * TICK))

  def _flush(self) -> List[BlockEvent]:
    out: List[BlockEvent] = []
    for item in self._queue:
      if isinstance(item, _TextRun):
        out.append(TextDelta(text=item.text, channel=item.channel))
      else:
        out.append(item)
        if isinstance(item, StreamEnd):
          self._done = True
    self._queue.clear()
    return out
