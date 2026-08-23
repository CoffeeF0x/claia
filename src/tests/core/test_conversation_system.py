"""System message is a generate-time argument, not conversation state."""

from claia.core.data import Conversation
from claia.core.data.models.conversation.message_sequence import MessageSequence
from claia.core.definitions.model_definition import ModelDefinition
from claia.core.enums.conversation import MessageRole
from claia.core.enums.data import ArtifactType
from claia.core.enums.events import EventType


def test_to_dict_omits_prompt():
  conv = Conversation(title="t")
  data = conv.to_dict()
  assert "prompt" not in data
  assert not hasattr(conv, "prompt")


def test_from_dict_ignores_legacy_prompt_key():
  conv = Conversation.from_dict({
    "title": "legacy",
    "prompt": {"system": "ignored"},
    "messages": [],
    "events": [],
  })
  assert not hasattr(conv, "prompt")
  sequence = conv.to_message_sequence([ArtifactType.TEXT])
  assert sequence.system is None


def test_to_message_sequence_takes_system():
  conv = Conversation(title="t")
  conv.add_message(MessageRole.USER, "hi")
  sequence = conv.to_message_sequence(
    [ArtifactType.TEXT],
    system="  Be brief  ",
  )
  assert sequence.system == "Be brief"
  assert sequence.messages[0].role == MessageRole.SYSTEM
  assert sequence.messages[0].content == "Be brief"
  assert conv.to_dict().get("prompt") is None


def test_to_message_sequence_blank_system_is_none():
  conv = Conversation(title="t")
  conv.add_message(MessageRole.USER, "hi")
  sequence = conv.to_message_sequence([ArtifactType.TEXT], system="   ")
  assert sequence.system is None


def test_to_model_inputs_forwards_system():
  conv = Conversation(title="t")
  conv.add_message(MessageRole.USER, "hi")
  sequence = conv.to_model_inputs(
    ModelDefinition(inputs=[ArtifactType.TEXT, MessageSequence]),
    system="Stay terse",
  )
  assert isinstance(sequence, MessageSequence)
  assert sequence.system == "Stay terse"
  assert sequence.messages[0].role == MessageRole.SYSTEM


def test_unknown_event_type_is_skipped():
  conv = Conversation.from_dict({
    "title": "t",
    "events": [
      {
        "event_type": "PROMPT_CHANGED",
        "entity_id": "x",
        "metadata": {"new_prompt": "gone"},
      },
      {
        "event_type": "TITLE_CHANGED",
        "entity_id": "x",
        "metadata": {"new_title": "kept"},
      },
    ],
  })
  types = [e.event_type for e in conv.events]
  assert "PROMPT_CHANGED" not in EventType.__members__
  assert EventType.TITLE_CHANGED in types
  assert EventType.CONVERSATION_CREATED not in types


def test_sequence_system_is_a_turn_not_a_sidecar():
  from claia.core.data.models.conversation.message import Message
  from claia.core.data.models.conversation.message_sequence import MessageSequence

  sequence = MessageSequence(
    messages=[Message(role=MessageRole.USER, content="hi")],
    system="Be brief",
  )
  assert sequence.messages[0].role == MessageRole.SYSTEM
  assert sequence.messages[0].content == "Be brief"
  assert sequence.system == "Be brief"
  data = sequence.to_dict()
  assert "system" not in data
  assert data["messages"][0]["role"] == MessageRole.SYSTEM.value


def test_sequence_system_is_derived_from_turns():
  from claia.core.data.models.conversation.message import Message
  from claia.core.data.models.conversation.message_sequence import MessageSequence

  sequence = MessageSequence(messages=[
    Message(role=MessageRole.SYSTEM, content="A"),
    Message(role=MessageRole.SYSTEM, content="B"),
    Message(role=MessageRole.USER, content="hi"),
  ])
  assert sequence.system == "A\n\nB"


def test_sequence_from_dict_accepts_leftover_system_key():
  from claia.core.data.models.conversation.message import Message
  from claia.core.data.models.conversation.message_sequence import MessageSequence

  sequence = MessageSequence.from_dict({
    "messages": [Message(role=MessageRole.USER, content="hi").to_dict()],
    "system": "Old sidecar",
  })
  assert sequence.messages[0].role == MessageRole.SYSTEM
  assert sequence.messages[0].content == "Old sidecar"
  assert sequence.system == "Old sidecar"


def test_ordered_sequence_keeps_system_at_front():
  from claia.core.data.models.conversation.message import Message
  from claia.core.data.models.conversation.message_sequence import (
    MessageSequenceOrdered,
  )

  sequence = MessageSequenceOrdered(
    messages=[
      Message(role=MessageRole.ASSISTANT, content="dropped"),
      Message(role=MessageRole.USER, content="one"),
      Message(role=MessageRole.USER, content="two"),
    ],
    system="Stay terse",
  )
  assert sequence.messages[0].role == MessageRole.SYSTEM
  assert sequence.messages[0].content == "Stay terse"
  assert sequence.messages[1].role == MessageRole.USER
  assert sequence.messages[1].content == "one\ntwo"
  assert sequence.system == "Stay terse"


def test_to_message_sequence_includes_tool_result_utilities():
  from claia.core.data.artifacts import ToolArtifact
  from claia.core.enums.parser import TagType

  conv = Conversation(title="t")
  user = conv.add_message(MessageRole.USER, "hi")
  assistant = conv.add_message(MessageRole.ASSISTANT, "[TOOL_CALL]{}[/TOOL_CALL]")
  thinking = conv.append_utility(
    tag_type=TagType.THINKING,
    content="ponder",
    source_message_id=assistant.message_id,
  )
  tool = conv.append_utility(
    tag_type=TagType.TOOL,
    content='{"name":"demo.echo"}',
    source_message_id=assistant.message_id,
  )
  conv.attach_artifact(tool.message_id, ToolArtifact.from_result("demo.echo", "pong"))
  conv.add_message(MessageRole.ASSISTANT, "done")

  sequence = conv.to_message_sequence([ArtifactType.TEXT])
  roles = [m.role for m in sequence.messages]
  assert roles == [
    MessageRole.USER,
    MessageRole.ASSISTANT,
    MessageRole.UTILITY,
    MessageRole.ASSISTANT,
  ]
  utility = sequence.messages[2]
  results = utility.tool_result_artifacts()
  assert len(results) == 1
  assert results[0].content == "pong"
  assert utility.content == ""
  assert user.content == "hi"
  assert thinking.tag_type is TagType.THINKING
  assert all(m.tag_type is not TagType.THINKING for m in sequence.messages)


def test_ordered_sequence_keeps_utility_between_assistants():
  from claia.core.data import Message
  from claia.core.data.artifacts import ToolArtifact
  from claia.core.data.models.conversation.message_sequence import (
    MessageSequenceOrdered,
  )
  from claia.core.enums.parser import TagType

  utility = Message(
    role=MessageRole.UTILITY,
    tag_type=TagType.TOOL,
    artifacts=[ToolArtifact.from_result("demo.echo", "pong")],
  )
  sequence = MessageSequenceOrdered(
    messages=[
      Message(role=MessageRole.USER, content="hi"),
      Message(role=MessageRole.ASSISTANT, content="calling"),
      utility,
      Message(role=MessageRole.ASSISTANT, content="done"),
    ],
  )
  assert [m.role for m in sequence.messages] == [
    MessageRole.USER,
    MessageRole.ASSISTANT,
    MessageRole.UTILITY,
    MessageRole.ASSISTANT,
  ]
  assert sequence.messages[2].tool_result_artifacts()[0].content == "pong"


def test_conversation_created_metadata_has_no_system_prompt():
  conv = Conversation(title="named")
  created = conv.events[0]
  assert created.event_type == EventType.CONVERSATION_CREATED
  assert "system_prompt" not in created.metadata
  assert created.metadata["title"] == "named"
