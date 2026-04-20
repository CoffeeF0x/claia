"""
Jitter-buffered renderer for streaming text output.

Decouples token arrival from terminal rendering so bursty streams
(several deltas arriving in one TCP segment, server-side batching, etc.)
appear as smooth typing at a rate that tracks the API's average
throughput.

Usage:
    renderer = PacedRenderer()
    renderer.start()
    process.on("token", renderer.feed)
    # ...later...
    renderer.finish(drain=True)
"""

# External dependencies
import sys
import threading
import time
import logging
from collections import deque



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



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
