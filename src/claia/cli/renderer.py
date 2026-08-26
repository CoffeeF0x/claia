"""
Terminal renderers for streamed output.

- ``BlockRenderer`` — plaintext sink for the stream router's block
  events: assistant text to stdout, tool calls and artifact notices
  as dim one-liners, thinking and a usage summary in verbose mode,
  errors to stderr. ANSI styling and pacing apply only when stdout
  is a TTY; piped output is raw. ``NO_COLOR`` is respected.
- ``PacedRenderer`` — jitter buffer that decouples token arrival
  from terminal writes so bursty streams (several deltas arriving
  in one TCP segment, server-side batching, etc.) appear as smooth
  typing at a rate that tracks the source's average throughput.
"""

# External dependencies
import os
import sys
import threading
import time
import logging
from collections import deque
from typing import Iterable, Optional

from ..core.enums.task import TaskStatus
from .stream import (
  ArtifactNotice,
  BlockEvent,
  Channel,
  StreamEnd,
  TextDelta,
  ToolCall,
)



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                              FUNCTIONS                               #
########################################################################
def stream_summary(end: StreamEnd) -> Optional[str]:
  """One-line usage/duration summary for a stream end, or None.

  Shared presentation: the one-shot renderer prints it bracketed in
  verbose mode; the TUI status bar shows it after every turn.
  """
  parts = []
  usage = end.usage
  if usage is not None:
    tokens = []
    if usage.prompt_tokens is not None:
      tokens.append(f"{usage.prompt_tokens} in")
    if usage.completion_tokens is not None:
      tokens.append(f"{usage.completion_tokens} out")
    if not tokens and usage.total_tokens is not None:
      tokens.append(f"{usage.total_tokens} total")
    if tokens:
      parts.append("tokens: " + ", ".join(tokens))
  if end.metrics is not None and end.metrics.duration is not None:
    parts.append(f"{end.metrics.duration:.2f}s")
  return " | ".join(parts) if parts else None



########################################################################
#                               CLASSES                                #
########################################################################
class PacedRenderer:
  """
  Smooth out bursty token streams by rendering chars at an adaptive rate.

  The producer side (``feed``) is called from the worker thread whenever
  a token arrives. Chars are appended to an internal buffer and a moving
  estimate of the arrival rate is updated.

  A background renderer thread pops chars one at a time and writes them
  to the sink, sleeping between chars at an interval chosen to make the
  output rate track the arrival rate plus a correction term proportional
  to how full the buffer is. This is a P-controller on buffer occupancy
  with the arrival rate as the feedforward signal.
  """

  def __init__(
    self,
    sink=None,
    target_latency_s: float = 0.15,    # backlog we aim to maintain
    catchup_horizon_s: float = 0.5,    # how fast we correct toward target
    min_rate: float = 25.0,            # floor render rate (chars/sec)
    max_rate: float = 400.0,           # ceiling render rate (chars/sec)
    initial_rate: float = 60.0,        # used until we have arrival data
    ema_alpha: float = 0.25,           # arrival-rate smoothing factor
  ):
    self._sink = sink if sink is not None else sys.stdout
    self._target_latency = target_latency_s
    self._tau = catchup_horizon_s
    self._min_rate = min_rate
    self._max_rate = max_rate
    self._alpha = ema_alpha

    self._buf: deque = deque()
    self._lock = threading.Lock()
    self._cv = threading.Condition(self._lock)
    self._done = False
    self._started = False

    self._rate = initial_rate
    self._last_arrival = None

    self._thread = threading.Thread(
      target=self._run,
      daemon=True,
      name="PacedRenderer"
    )

  # ── Producer side ────────────────────────────────────────────────────

  def start(self) -> None:
    """Start the background renderer thread. Idempotent."""
    if self._started:
      return
    self._started = True
    self._thread.start()

  def feed(self, chunk: str) -> None:
    """Enqueue a chunk of text and update the arrival-rate estimate."""
    if not chunk:
      return
    now = time.monotonic()
    with self._cv:
      if self._last_arrival is not None:
        dt = max(now - self._last_arrival, 1e-3)
        inst = len(chunk) / dt
        self._rate = self._alpha * inst + (1 - self._alpha) * self._rate
      self._last_arrival = now
      self._buf.extend(chunk)
      self._cv.notify()

  def finish(self, drain: bool = True, timeout: float = 30.0) -> None:
    """
    Signal end of stream.

    When ``drain`` is True (default), block until the renderer has
    flushed any remaining buffered chars. When False, return immediately
    and let the renderer terminate without printing the rest.
    """
    with self._cv:
      self._done = True
      if not drain:
        self._buf.clear()
      self._cv.notify_all()
    if drain and self._started:
      self._thread.join(timeout=timeout)

  # ── Renderer thread ──────────────────────────────────────────────────

  def _run(self) -> None:
    try:
      while True:
        with self._cv:
          while not self._buf and not self._done:
            self._cv.wait()
          if not self._buf and self._done:
            return
          ch = self._buf.popleft()
          backlog = len(self._buf)
          rate = self._rate
          done = self._done

        try:
          self._sink.write(ch)
          self._sink.flush()
        except Exception as e:
          logger.error(f"PacedRenderer sink write failed: {e}")
          return

        if done and backlog == 0:
          return

        # P-controller on backlog occupancy. When the stream has ended,
        # avoid the under-target slowdown so we drain at a steady pace.
        target_backlog = max(1.0, self._target_latency * rate)
        error = backlog - target_backlog
        render_rate = rate + error / self._tau
        if done:
          render_rate = max(render_rate, rate)
        render_rate = max(self._min_rate, min(self._max_rate, render_rate))

        time.sleep(1.0 / render_rate)
    except Exception as e:
      logger.exception(f"PacedRenderer thread crashed: {e}")


class BlockRenderer:
  """Plaintext renderer for stream-router block events.

  Default output: TEXT deltas verbatim, thinking dropped, tool calls
  as one dim ``[tool <name>]`` line, artifacts as ``[saved: <name>]``,
  stream errors to stderr. Verbose adds dim ``[thinking]`` blocks and
  one usage/duration summary line at stream end.

  ``tty``, ``color``, and ``paced`` default from the output stream:
  a TTY gets ANSI dim styling (unless ``NO_COLOR`` is set) and paced
  typing via ``PacedRenderer``; piped output is raw and immediate.
  """

  DIM = "\x1b[2m"
  RESET = "\x1b[0m"

  def __init__(
    self,
    out=None,
    err=None,
    verbose: bool = False,
    tty: Optional[bool] = None,
    color: Optional[bool] = None,
    paced: Optional[bool] = None,
  ):
    self._out = out if out is not None else sys.stdout
    self._err = err if err is not None else sys.stderr
    self._verbose = verbose
    if tty is None:
      tty = getattr(self._out, "isatty", lambda: False)()
    self._color = (tty and not os.environ.get("NO_COLOR")) if color is None else color
    self._paced = tty if paced is None else paced
    self._pacer: Optional[PacedRenderer] = None
    self._at_line_start = True
    self._closed = False

  # ── Event handling ───────────────────────────────────────────────────

  def handle_all(self, events: Iterable[BlockEvent]) -> None:
    for event in events:
      self.handle(event)

  def handle(self, event: BlockEvent) -> None:
    if isinstance(event, TextDelta):
      if event.channel is Channel.THINKING:
        if self._verbose:
          self._write_notice(f"[thinking] {event.text}")
      else:
        self._write(event.text)
    elif isinstance(event, ToolCall):
      self._write_notice(f"[tool {event.name or 'unknown'}]")
    elif isinstance(event, ArtifactNotice):
      self._write_notice(f"[saved: {event.name}]")
    elif isinstance(event, StreamEnd):
      self._end(event)

  # ── Output plumbing ──────────────────────────────────────────────────

  def _write(self, text: str) -> None:
    if not text:
      return
    self._at_line_start = text.endswith("\n")
    if self._paced:
      if self._pacer is None:
        self._pacer = PacedRenderer(sink=self._out)
        self._pacer.start()
      self._pacer.feed(text)
    else:
      self._sink_write(text)

  def _sink_write(self, text: str) -> None:
    # Downstream may close the pipe mid-stream (`claia … | head`);
    # go quiet and let the task run to completion.
    if self._closed:
      return
    try:
      self._out.write(text)
      self._out.flush()
    except BrokenPipeError:
      self._closed = True

  def _write_notice(self, line: str) -> None:
    prefix = "" if self._at_line_start else "\n"
    self._write(prefix + self._dim(line) + "\n")

  def _dim(self, text: str) -> str:
    return f"{self.DIM}{text}{self.RESET}" if self._color else text

  def _end(self, end: StreamEnd) -> None:
    # On failure, drop whatever the pacer is still holding — the
    # error line should not wait behind a slow drain.
    drain = end.status is not TaskStatus.FAILED
    if not self._at_line_start and drain:
      self._write("\n")
    if self._pacer is not None:
      self._pacer.finish(drain=drain)
      self._pacer = None
    if self._verbose:
      summary = stream_summary(end)
      if summary:
        self._sink_write(self._dim(f"[{summary}]") + "\n")
    if end.error:
      prefix = "" if self._at_line_start else "\n"
      self._err.write(f"{prefix}Error: {end.error}\n")
      self._err.flush()
