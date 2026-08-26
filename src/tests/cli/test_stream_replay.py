"""
Golden tests for turn replay.

Fixture conversations are built the way the agent persists them —
assistant messages carrying the raw streamed text, UTILITY siblings
for parsed spans (source indices for MANUAL/thinking, none for
NATIVE), ``ToolArtifact`` results attached to TOOL utilities — and
replay must produce the block-event sequence the router would have
emitted live.
"""

# External dependencies
import json

# Internal dependencies
from claia.cli.stream import (
  ArtifactNotice,
  Channel,
  StreamEnd,
  StreamRouter,
  TextDelta,
  ToolCall,
  ToolResult,
  ToolSource,
  replay_turn,
)
from claia.core.data import Conversation
from claia.core.data.artifacts import ToolArtifact
from claia.core.data.chunks import TextChunk
from claia.core.data.models import ImageArtifact
from claia.core.enums.conversation import MessageRole
from claia.core.enums.data import ImageFormat
from claia.core.enums.parser import TagType
from claia.core.enums.task import TaskStatus



########################################################################
#                               HELPERS                                #
########################################################################
def assistant_turn(content):
  """A conversation holding one assistant message with ``content``."""
  conversation = Conversation()
  message = conversation.add_message(MessageRole.ASSISTANT, content)
  return conversation, message


def utilities_of(conversation, message):
  return [
    m for m in conversation.get_thread(include_utility=True)
    if m.role is MessageRole.UTILITY
    and m.source_message_id == message.message_id
  ]


def tag_span(content, open_token, close_token):
  """(start, end) source indices of the first ``open…close`` span."""
  start = content.index(open_token)
  end = content.index(close_token) + len(close_token)
  return start, end


def normalized(events):
  """Merge adjacent same-channel text deltas; drop non-content events.

  Live streaming and replay chunk text differently; after merging,
  the sequences must be identical.
  """
  out = []
  for event in events:
    if isinstance(event, (StreamEnd, ToolResult)):
      continue
    if (
      isinstance(event, TextDelta)
      and out
      and isinstance(out[-1], TextDelta)
      and out[-1].channel is event.channel
    ):
      out[-1] = TextDelta(
        text=out[-1].text + event.text, channel=event.channel,
      )
    else:
      out.append(event)
  return out



########################################################################
#                            THINKING SPANS                            #
########################################################################
class TestThinkingReplay:
  def test_text_splits_around_a_thinking_span(self):
    content = "Answer.<think>hidden</think> More."
    conversation, message = assistant_turn(content)
    start, end = tag_span(content, "<think>", "</think>")
    conversation.append_utility(
      tag_type=TagType.THINKING,
      content="hidden",
      source_message_id=message.message_id,
      start_index=start,
      end_index=end,
    )

    events = replay_turn(message, utilities_of(conversation, message))
    assert events == [
      TextDelta(text="Answer.", channel=Channel.TEXT),
      TextDelta(text="hidden", channel=Channel.THINKING),
      TextDelta(text=" More.", channel=Channel.TEXT),
    ]

  def test_plain_turn_is_one_text_delta(self):
    _, message = assistant_turn("Just text.")
    assert replay_turn(message, []) == [
      TextDelta(text="Just text.", channel=Channel.TEXT),
    ]



########################################################################
#                          MANUAL TOOL CALLS                           #
########################################################################
class TestManualToolReplay:
  PAYLOAD = '{"name": "sample.echo", "parameters": {"message": "hi"}}'

  def make_turn(self, with_result=True, attributes=None):
    content = f"Check.[TOOL_CALL]{self.PAYLOAD}[/TOOL_CALL] Done."
    conversation, message = assistant_turn(content)
    start, end = tag_span(content, "[TOOL_CALL]", "[/TOOL_CALL]")
    utility = conversation.append_utility(
      tag_type=TagType.TOOL,
      content=self.PAYLOAD,
      source_message_id=message.message_id,
      start_index=start,
      end_index=end,
      attributes=attributes,
    )
    if with_result:
      conversation.attach_artifact(
        utility.message_id,
        ToolArtifact.from_result("sample.echo", "hi"),
      )
    return conversation, message

  def test_manual_call_with_result(self):
    conversation, message = self.make_turn()
    events = replay_turn(message, utilities_of(conversation, message))
    assert events == [
      TextDelta(text="Check.", channel=Channel.TEXT),
      ToolCall(
        name="sample.echo",
        args=self.PAYLOAD,
        call_id=None,
        source=ToolSource.MANUAL,
      ),
      ToolResult(name="sample.echo", body="hi", call_id=None),
      TextDelta(text=" Done.", channel=Channel.TEXT),
    ]

  def test_manual_call_without_result_has_no_result_event(self):
    conversation, message = self.make_turn(with_result=False)
    events = replay_turn(message, utilities_of(conversation, message))
    assert not any(isinstance(e, ToolResult) for e in events)

  def test_name_prefers_the_tag_attribute(self):
    conversation, message = self.make_turn(
      attributes={"name": "other.tool"},
    )
    events = replay_turn(message, utilities_of(conversation, message))
    call = next(e for e in events if isinstance(e, ToolCall))
    assert call.name == "other.tool"

  def test_replay_matches_the_router_for_the_same_stream(self):
    conversation, message = self.make_turn()
    replayed = replay_turn(message, utilities_of(conversation, message))

    router = StreamRouter()
    live = list(router.feed(TextChunk(data=message.content)))
    live.extend(router.end(TaskStatus.COMPLETED))
    assert normalized(replayed) == normalized(live)



########################################################################
#                          NATIVE TOOL CALLS                           #
########################################################################
class TestNativeToolReplay:
  def test_native_call_unwraps_the_stored_envelope(self):
    parameters = {"a": 1, "b": 2}
    envelope = json.dumps({"name": "sample.add", "parameters": parameters})
    conversation, message = assistant_turn("Running.")
    utility = conversation.append_utility(
      tag_type=TagType.TOOL,
      content=envelope,
      source_message_id=message.message_id,
    )
    conversation.attach_artifact(
      utility.message_id,
      ToolArtifact.from_result("sample.add", "3.0", call_id="c1"),
    )

    events = replay_turn(message, utilities_of(conversation, message))
    assert events == [
      TextDelta(text="Running.", channel=Channel.TEXT),
      ToolCall(
        name="sample.add",
        args=json.dumps(parameters),
        call_id="c1",
        source=ToolSource.NATIVE,
      ),
      ToolResult(name="sample.add", body="3.0", call_id="c1"),
    ]



########################################################################
#                               ARTIFACTS                              #
########################################################################
class TestArtifactReplay:
  def test_extra_message_artifacts_become_notices(self):
    conversation, message = assistant_turn("Here.")
    conversation.attach_artifact(
      message.message_id,
      ImageArtifact.from_bytes(
        image_data=b"x", name="pic.png", format=ImageFormat.PNG,
      ),
    )
    events = replay_turn(message, utilities_of(conversation, message))
    assert events == [
      TextDelta(text="Here.", channel=Channel.TEXT),
      ArtifactNotice(name="pic.png"),
    ]
