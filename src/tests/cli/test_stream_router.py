"""
Golden tests for the CLI stream router.

Recorded chunk sequences go in; the expected block-event sequences
come out. Covers live text emission, tags split across chunk
boundaries, NATIVE ToolChunks, MANUAL tool tags, think spans,
unclosed tags at stream end, and parse errors passed as metadata.
"""

# External dependencies
from types import SimpleNamespace
from typing import List

# Internal dependencies
from claia.cli.stream import (
  ArtifactNotice,
  Channel,
  StreamEnd,
  StreamRouter,
  TextDelta,
  ToolCall,
  ToolSource,
)
from claia.core.data.chunks import (
  MetricsChunk,
  TextChunk,
  ToolChunk,
  UsageChunk,
)
from claia.core.enums.task import TaskStatus



########################################################################
#                               HELPERS                                #
########################################################################
def run_stream(chunks, status=TaskStatus.COMPLETED, error=None):
  """Feed all chunks, end the stream, return the full event list."""
  router = StreamRouter()
  events = []
  for chunk in chunks:
    events.extend(router.feed(chunk))
  events.extend(router.end(status, error=error))
  return events


def text_of(events, channel=Channel.TEXT) -> str:
  return "".join(
    e.text for e in events
    if isinstance(e, TextDelta) and e.channel is channel
  )


def tool_calls(events) -> List[ToolCall]:
  return [e for e in events if isinstance(e, ToolCall)]


def stream_end(events) -> StreamEnd:
  assert isinstance(events[-1], StreamEnd)
  return events[-1]



########################################################################
#                              PLAIN TEXT                              #
########################################################################
class TestPlainText:
  def test_text_streams_live_not_at_flush(self):
    router = StreamRouter()
    first = list(router.feed(TextChunk(data="Hello ")))
    assert first == [TextDelta(text="Hello ", channel=Channel.TEXT)]

    second = list(router.feed(TextChunk(data="world")))
    assert second == [TextDelta(text="world", channel=Channel.TEXT)]

    final = list(router.end(TaskStatus.COMPLETED))
    assert len(final) == 1  # only the StreamEnd; no re-emitted text
    assert isinstance(final[0], StreamEnd)

  def test_partial_tag_prefix_is_held_back(self):
    router = StreamRouter()
    events = list(router.feed(TextChunk(data="a<thi")))
    # "<thi" may still become <think>; only "a" is safe to emit.
    assert events == [TextDelta(text="a", channel=Channel.TEXT)]

  def test_end_flushes_held_text(self):
    router = StreamRouter()
    list(router.feed(TextChunk(data="tail<")))
    events = list(router.end(TaskStatus.COMPLETED))
    assert events[0] == TextDelta(text="<", channel=Channel.TEXT)
    assert isinstance(events[1], StreamEnd)



########################################################################
#                             THINK SPANS                              #
########################################################################
class TestThinkSpans:
  def test_think_span_becomes_thinking_delta(self):
    events = run_stream([TextChunk(data="a<think>deep</think>b")])
    assert events[:3] == [
      TextDelta(text="a", channel=Channel.TEXT),
      TextDelta(text="deep", channel=Channel.THINKING),
      TextDelta(text="b", channel=Channel.TEXT),
    ]

  def test_think_span_split_across_chunks(self):
    events = run_stream([
      TextChunk(data="a<thi"),
      TextChunk(data="nk>hidden</th"),
      TextChunk(data="ink>b"),
    ])
    assert text_of(events) == "ab"
    assert text_of(events, Channel.THINKING) == "hidden"

  def test_unclosed_think_at_stream_end(self):
    events = run_stream([TextChunk(data="before<think>never shown")])
    assert text_of(events) == "before"
    assert text_of(events, Channel.THINKING) == ""
    end = stream_end(events)
    assert len(end.parse_errors) == 1
    assert end.parse_errors[0].reason == "unclosed_tags"



########################################################################
#                             TOOL CALLS                               #
########################################################################
class TestToolCalls:
  def test_native_tool_chunk(self):
    chunk = ToolChunk(
      tool_name="sample.echo",
      payload={"text": "hi"},
      call_id="call-1",
    )
    events = run_stream([chunk])
    calls = tool_calls(events)
    assert len(calls) == 1
    assert calls[0].name == "sample.echo"
    assert calls[0].args == '{"text": "hi"}'
    assert calls[0].call_id == "call-1"
    assert calls[0].source is ToolSource.NATIVE

  def test_manual_tool_tag_name_from_payload(self):
    payload = '{"name": "sample.echo", "parameters": {"text": "hi"}}'
    events = run_stream([
      TextChunk(data=f"[TOOL_CALL]{payload}[/TOOL_CALL]"),
    ])
    calls = tool_calls(events)
    assert len(calls) == 1
    assert calls[0].name == "sample.echo"
    assert calls[0].args == payload
    assert calls[0].source is ToolSource.MANUAL

  def test_manual_tool_tag_name_from_attribute(self):
    events = run_stream([
      TextChunk(data='[TOOL_CALL name=sample.echo]{"text": "hi"}[/TOOL_CALL]'),
    ])
    calls = tool_calls(events)
    assert len(calls) == 1
    assert calls[0].name == "sample.echo"

  def test_manual_tool_tag_malformed_payload(self):
    events = run_stream([
      TextChunk(data="[TOOL_CALL]not json[/TOOL_CALL]"),
    ])
    calls = tool_calls(events)
    assert len(calls) == 1
    assert calls[0].name == ""
    assert calls[0].args == "not json"

  def test_tool_tag_split_at_every_boundary(self):
    fixture = (
      'pre [TOOL_CALL]{"name": "sample.echo", "parameters": {}}'
      "[/TOOL_CALL] mid <think>t</think> post"
    )
    for i in range(1, len(fixture)):
      events = run_stream([
        TextChunk(data=fixture[:i]),
        TextChunk(data=fixture[i:]),
      ])
      assert text_of(events) == "pre  mid  post", f"split at {i}"
      assert text_of(events, Channel.THINKING) == "t", f"split at {i}"
      calls = tool_calls(events)
      assert len(calls) == 1, f"split at {i}"
      assert calls[0].name == "sample.echo", f"split at {i}"



########################################################################
#                        OTHER TAGS AND ERRORS                         #
########################################################################
class TestTagsAndErrors:
  def test_reference_span_renders_as_text_content(self):
    events = run_stream([TextChunk(data="x[REF]cite[/REF]y")])
    assert text_of(events) == "xcitey"

  def test_mismatched_close_is_metadata_not_content(self):
    events = run_stream([
      TextChunk(data="<think>abc[/TOOL_CALL]</think>"),
    ])
    assert text_of(events, Channel.THINKING) == "abc[/TOOL_CALL]"
    end = stream_end(events)
    assert any(e.reason == "mismatched_close" for e in end.parse_errors)



########################################################################
#                        ACCOUNTING AND NOTICES                        #
########################################################################
class TestAccountingAndNotices:
  def test_usage_and_metrics_collected_on_stream_end(self):
    usage = UsageChunk(prompt_tokens=10, completion_tokens=20)
    metrics = MetricsChunk(duration=1.5)
    events = run_stream([TextChunk(data="hi"), usage, metrics])
    assert text_of(events) == "hi"
    end = stream_end(events)
    assert end.usage is usage
    assert end.metrics is metrics

  def test_artifact_notice(self):
    router = StreamRouter()
    events = list(router.feed_artifact(SimpleNamespace(name="pic.png")))
    assert events == [ArtifactNotice(name="pic.png")]

  def test_error_stream_end(self):
    events = run_stream(
      [TextChunk(data="partial")],
      status=TaskStatus.FAILED,
      error="model exploded",
    )
    end = stream_end(events)
    assert end.status is TaskStatus.FAILED
    assert end.error == "model exploded"
