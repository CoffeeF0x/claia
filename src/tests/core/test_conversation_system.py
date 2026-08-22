"""System message is a generate-time argument, not conversation state."""

from claia.core.data import Conversation, EventType
from claia.core.data.models.conversation.message_sequence import MessageSequence
from claia.core.deployments.dummy import DummyDeployment
from claia.core.definitions.model_definition import ModelDefinition
from claia.core.enums.conversation import MessageRole
from claia.core.enums.data import ArtifactType


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
  assert conv.to_dict().get("prompt") is None


def test_to_message_sequence_blank_system_is_none():
  conv = Conversation(title="t")
  conv.add_message(MessageRole.USER, "hi")
  sequence = conv.to_message_sequence([ArtifactType.TEXT], system="   ")
  assert sequence.system is None


def test_translate_forwards_system():
  conv = Conversation(title="t")
  conv.add_message(MessageRole.USER, "hi")
  sequence = DummyDeployment().translate(
    conv,
    ModelDefinition(inputs=[ArtifactType.TEXT, MessageSequence]),
    system="Stay terse",
  )
  assert isinstance(sequence, MessageSequence)
  assert sequence.system == "Stay terse"


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


def test_conversation_created_metadata_has_no_system_prompt():
  conv = Conversation(title="named")
  created = conv.events[0]
  assert created.event_type == EventType.CONVERSATION_CREATED
  assert "system_prompt" not in created.metadata
  assert created.metadata["title"] == "named"
