"""Architecture-layer formatting of message sequences, including tool utilities."""

from claia.core.architectures.dummy.dummy import DummyArchitecture
from claia.core.data import Message, MessageSequence, MessageSequenceOrdered
from claia.core.data.artifacts import ToolArtifact
from claia.core.enums.conversation import MessageRole
from claia.core.enums.parser import TagType


def _utility(name: str, body: str) -> Message:
  return Message(
    role=MessageRole.UTILITY,
    tag_type=TagType.TOOL,
    artifacts=[ToolArtifact.from_result(name, body)],
  )


def test_format_messages_maps_tool_utility_to_user_result_block():
  sequence = MessageSequence(messages=[
    Message(role=MessageRole.USER, content="hi"),
    Message(role=MessageRole.ASSISTANT, content="calling"),
    _utility("demo.echo", "pong"),
    Message(role=MessageRole.ASSISTANT, content="done"),
  ])
  formatted = DummyArchitecture("dummy").format_messages(sequence)
  assert formatted == [
    {"role": "user", "content": "hi"},
    {"role": "assistant", "content": "calling"},
    {"role": "user", "content": ToolArtifact.format_result("demo.echo", "pong")},
    {"role": "assistant", "content": "done"},
  ]


def test_coalesce_consecutive_roles_merges_mapped_tool_results():
  formatted = DummyArchitecture("dummy").format_messages(
    MessageSequence(messages=[
      Message(role=MessageRole.USER, content="hi"),
      Message(role=MessageRole.ASSISTANT, content="calling"),
      _utility("math.add", "5"),
      _utility("demo.shout", "HI"),
    ])
  )
  merged = DummyArchitecture.coalesce_consecutive_roles(formatted)
  assert merged[-1]["role"] == "user"
  assert ToolArtifact.format_result("math.add", "5") in merged[-1]["content"]
  assert ToolArtifact.format_result("demo.shout", "HI") in merged[-1]["content"]


def test_ordered_sequence_then_format_keeps_utility_between_assistants():
  sequence = MessageSequenceOrdered(messages=[
    Message(role=MessageRole.USER, content="hi"),
    Message(role=MessageRole.ASSISTANT, content="calling"),
    _utility("demo.echo", "pong"),
    Message(role=MessageRole.ASSISTANT, content="done"),
  ])
  formatted = DummyArchitecture("dummy").format_messages(sequence)
  assert [m["role"] for m in formatted] == ["user", "assistant", "user", "assistant"]
  assert formatted[2]["content"] == ToolArtifact.format_result("demo.echo", "pong")
