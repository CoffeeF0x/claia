"""
Golden tests for the plaintext block renderer.

Block events go in; the expected terminal output comes out, in
default and verbose modes, for TTY and non-TTY (piped) variants.
"""

# External dependencies
import io

# Internal dependencies
from claia.cli.renderer import BlockRenderer
from claia.cli.stream import (
  ArtifactNotice,
  Channel,
  StreamEnd,
  TextDelta,
  ToolCall,
)
from claia.core.data.chunks import MetricsChunk, UsageChunk
from claia.core.enums.task import TaskStatus


DIM = "\x1b[2m"
RESET = "\x1b[0m"


########################################################################
#                               HELPERS                                #
########################################################################
def render(events, **kwargs):
  out, err = io.StringIO(), io.StringIO()
  kwargs.setdefault("tty", False)
  renderer = BlockRenderer(out=out, err=err, **kwargs)
  renderer.handle_all(events)
  return out.getvalue(), err.getvalue()



########################################################################
#                             DEFAULT MODE                             #
########################################################################
class TestDefaultMode:
  def test_piped_output_is_raw_and_unstyled(self):
    out, err = render([
      TextDelta(text="Hello"),
      TextDelta(text="secret", channel=Channel.THINKING),
      ToolCall(name="sample.echo"),
      ArtifactNotice(name="pic.png"),
      TextDelta(text="done"),
      StreamEnd(status=TaskStatus.COMPLETED),
    ])
    assert out == "Hello\n[tool sample.echo]\n[saved: pic.png]\ndone\n"
    assert err == ""

  def test_thinking_dropped_by_default(self):
    out, _ = render([
      TextDelta(text="secret", channel=Channel.THINKING),
      StreamEnd(status=TaskStatus.COMPLETED),
    ])
    assert out == ""

  def test_nameless_tool_call(self):
    out, _ = render([
      ToolCall(name=""),
      StreamEnd(status=TaskStatus.COMPLETED),
    ])
    assert out == "[tool unknown]\n"

  def test_no_summary_without_verbose(self):
    out, _ = render([
      TextDelta(text="hi\n"),
      StreamEnd(
        status=TaskStatus.COMPLETED,
        usage=UsageChunk(prompt_tokens=1, completion_tokens=2),
        metrics=MetricsChunk(duration=0.5),
      ),
    ])
    assert out == "hi\n"

  def test_error_goes_to_stderr(self):
    out, err = render([
      TextDelta(text="partial"),
      StreamEnd(status=TaskStatus.FAILED, error="model exploded"),
    ])
    assert out == "partial"
    assert err == "\nError: model exploded\n"



########################################################################
#                             VERBOSE MODE                             #
########################################################################
class TestVerboseMode:
  def test_thinking_marked_and_summary_line(self):
    out, _ = render(
      [
        TextDelta(text="Hi"),
        TextDelta(text="think hard", channel=Channel.THINKING),
        StreamEnd(
          status=TaskStatus.COMPLETED,
          usage=UsageChunk(prompt_tokens=10, completion_tokens=20),
          metrics=MetricsChunk(duration=1.5),
        ),
      ],
      verbose=True,
    )
    assert out == "Hi\n[thinking] think hard\n[tokens: 10 in, 20 out | 1.50s]\n"

  def test_summary_with_metrics_only(self):
    out, _ = render(
      [StreamEnd(status=TaskStatus.COMPLETED, metrics=MetricsChunk(duration=2.0))],
      verbose=True,
    )
    assert out == "[2.00s]\n"

  def test_no_summary_when_nothing_collected(self):
    out, _ = render(
      [TextDelta(text="hi\n"), StreamEnd(status=TaskStatus.COMPLETED)],
      verbose=True,
    )
    assert out == "hi\n"



########################################################################
#                             TTY VARIANTS                             #
########################################################################
class TestTtyVariants:
  def test_tty_styles_notices_dim(self, monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    out, _ = render(
      [
        TextDelta(text="hi"),
        ToolCall(name="sample.echo"),
        StreamEnd(status=TaskStatus.COMPLETED),
      ],
      tty=True,
      paced=False,
    )
    assert out == f"hi\n{DIM}[tool sample.echo]{RESET}\n"

  def test_no_color_disables_styling(self, monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    out, _ = render(
      [ToolCall(name="sample.echo"), StreamEnd(status=TaskStatus.COMPLETED)],
      tty=True,
      paced=False,
    )
    assert out == "[tool sample.echo]\n"

  def test_paced_output_drains_on_stream_end(self, monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    out, _ = render(
      [TextDelta(text="hi"), StreamEnd(status=TaskStatus.COMPLETED)],
      tty=True,
      color=False,
    )
    assert out == "hi\n"
