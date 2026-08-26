"""
Unit tests for the TUI display pacer.

Pure logic — ticks are driven by hand, no Textual timer. Covers
drip ordering, structural-event barriers, the accelerated drain
once a graceful StreamEnd is queued, and the immediate flush on
CANCELLED/FAILED ends.
"""

# Internal dependencies
from claia.cli.stream import (
  ArtifactNotice,
  Channel,
  StreamEnd,
  TextDelta,
  ToolCall,
  ToolResult,
)
from claia.cli.tui.pacer import MAX_RATE, TICK, Pacer
from claia.core.enums.task import TaskStatus



########################################################################
#                               HELPERS                                #
########################################################################
def drain(pacer, max_ticks=10_000):
  """Tick until the queue empties; returns (events, tick_count)."""
  events = []
  ticks = 0
  while pacer.pending and ticks < max_ticks:
    events.extend(pacer.tick())
    ticks += 1
  return events, ticks


def joined(events, channel=Channel.TEXT):
  return "".join(
    e.text for e in events
    if isinstance(e, TextDelta) and e.channel is channel
  )



########################################################################
#                            DRIP ORDERING                             #
########################################################################
class TestDrip:
  def test_text_drips_in_order_over_multiple_ticks(self):
    text = "x" * 50 + "abcdefghij" + "y" * 40
    pacer = Pacer()
    assert pacer.feed([TextDelta(text=text)]) == []
    events, ticks = drain(pacer)
    assert joined(events) == text
    assert ticks > 1  # paced, not dumped
    cap = int(MAX_RATE * TICK)
    assert all(len(e.text) <= cap for e in events)

  def test_channel_runs_keep_their_order(self):
    pacer = Pacer()
    pacer.feed([
      TextDelta(text="aaa"),
      TextDelta(text="bbb", channel=Channel.THINKING),
      TextDelta(text="ccc"),
    ])
    events, _ = drain(pacer)
    order = [(e.channel, e.text) for e in events]
    assert "".join(t for c, t in order) == "aaabbbccc"
    channels = [c for c, _ in order]
    switch = channels.index(Channel.THINKING)
    assert all(c is Channel.TEXT for c in channels[:switch])
    assert joined(events, Channel.THINKING) == "bbb"

  def test_empty_deltas_are_dropped(self):
    pacer = Pacer()
    pacer.feed([TextDelta(text="")])
    assert not pacer.pending



########################################################################
#                               BARRIERS                               #
########################################################################
class TestBarriers:
  def test_structural_events_wait_for_preceding_text(self):
    before = "b" * 300
    call = ToolCall(name="sample.echo", args="{}")
    pacer = Pacer()
    pacer.feed([TextDelta(text=before), call, TextDelta(text="after")])

    seen_text = ""
    while pacer.pending:
      for event in pacer.tick():
        if isinstance(event, TextDelta):
          seen_text += event.text
        elif isinstance(event, ToolCall):
          # The barrier held: every preceding char is already out,
          # and it released on the same tick the text finished.
          assert seen_text == before
    assert seen_text == before + "after"

  def test_all_structural_kinds_are_barriers(self):
    pacer = Pacer()
    tail = [
      ToolCall(name="t", args=""),
      ToolResult(name="t", body="r"),
      ArtifactNotice(name="pic.png"),
      StreamEnd(status=TaskStatus.COMPLETED),
    ]
    pacer.feed([TextDelta(text="z" * 200), *tail])
    events, _ = drain(pacer)
    assert joined(events) == "z" * 200
    structural = [e for e in events if not isinstance(e, TextDelta)]
    assert structural == tail
    last_text = max(
      i for i, e in enumerate(events) if isinstance(e, TextDelta)
    )
    assert all(
      not isinstance(e, TextDelta) for e in events[last_text + 1:]
    )
    assert pacer.done



########################################################################
#                              END DRAIN                               #
########################################################################
class TestEndDrain:
  def test_graceful_end_is_not_an_instant_flush(self):
    pacer = Pacer()
    released = pacer.feed([
      TextDelta(text="w" * 2000),
      StreamEnd(status=TaskStatus.COMPLETED),
    ])
    assert released == []
    _, ticks = drain(pacer)
    assert ticks > 1

  def test_graceful_end_accelerates_the_drain(self):
    text = "w" * 2000
    plain = Pacer()
    plain.feed([TextDelta(text=text)])
    _, plain_ticks = drain(plain)

    ending = Pacer()
    ending.feed([TextDelta(text=text), StreamEnd(status=TaskStatus.COMPLETED)])
    events, ending_ticks = drain(ending)

    assert ending_ticks < plain_ticks
    assert joined(events) == text
    assert isinstance(events[-1], StreamEnd)
    assert ending.done



########################################################################
#                            INSTANT DRAIN                             #
########################################################################
class TestInstantDrain:
  def test_cancelled_end_flushes_everything_on_feed(self):
    pacer = Pacer()
    call = ToolCall(name="t", args="")
    pacer.feed([TextDelta(text="k" * 500), call])
    released = pacer.feed([StreamEnd(status=TaskStatus.CANCELLED)])
    assert joined(released) == "k" * 500
    assert released[-2] is call
    assert isinstance(released[-1], StreamEnd)
    assert pacer.done
    assert not pacer.pending
    assert pacer.tick() == []

  def test_failed_end_flushes_everything_on_feed(self):
    pacer = Pacer()
    pacer.feed([TextDelta(text="k" * 500)])
    released = pacer.feed([
      StreamEnd(status=TaskStatus.FAILED, error="boom"),
    ])
    assert joined(released) == "k" * 500
    assert isinstance(released[-1], StreamEnd)
    assert released[-1].error == "boom"
    assert pacer.done
