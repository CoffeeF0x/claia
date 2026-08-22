"""
Tests for utility messages.

Covers:
- ``MessageRole.UTILITY`` is a recognised role.
- ``Message`` carries the new utility fields (``tag_type``,
  ``source_message_id``, ``start_index``, ``end_index``,
  ``attributes``) and round-trips them through ``to_dict`` /
  ``from_dict``.
- Minimal serialized messages (without utility fields) deserialize
  with field defaults.
- ``Conversation.append_utility`` emits ``MESSAGE_CREATED`` with
  utility metadata, advances the active head, and stores the new
  message inline in the messages list.
- ``Conversation.get_thread`` filters utility messages by default and
  returns them when ``include_utility=True``.
- ``Conversation.get_messages`` honours ``include_utility`` and
  surfaces utility messages when the role filter explicitly asks
  for them.
- Conversation round-trip preserves utility messages and their
  fields end-to-end.
"""

# External dependencies
import pytest

# Internal dependencies
from claia.core.data import Conversation, EventType, Message
from claia.core.enums.conversation import MessageRole
from claia.core.parser.types import TagType


########################################################################
#                              ENUM                                    #
########################################################################
class TestUtilityRole:
  def test_utility_value(self):
    assert MessageRole.UTILITY.value == "utility"

  def test_utility_distinct_from_other_roles(self):
    others = {MessageRole.USER, MessageRole.ASSISTANT, MessageRole.SYSTEM, MessageRole.INTERNAL}
    assert MessageRole.UTILITY not in others


########################################################################
#                       MESSAGE FIELD CONSTRUCTION                     #
########################################################################
class TestMessageUtilityFields:
  def test_default_message_has_empty_utility_fields(self):
    msg = Message(role=MessageRole.USER, content="hello")
    assert msg.tag_type is None
    assert msg.source_message_id is None
    assert msg.start_index is None
    assert msg.end_index is None
    assert msg.attributes == {}
    assert msg.is_utility() is False

  def test_utility_message_carries_fields(self):
    msg = Message(
      role=MessageRole.UTILITY,
      content='{"name":"echo"}',
      tag_type=TagType.TOOL,
      source_message_id="src-1",
      start_index=10,
      end_index=42,
      attributes={"name": "echo"},
    )
    assert msg.is_utility()
    assert msg.tag_type == TagType.TOOL
    assert msg.source_message_id == "src-1"
    assert msg.start_index == 10
    assert msg.end_index == 42
    assert msg.attributes == {"name": "echo"}

  def test_tag_type_string_value_coerced_to_enum(self):
    """``Message`` accepts the serialized string form for ``tag_type``."""
    msg = Message(
      role=MessageRole.UTILITY,
      content="thinking aloud",
      tag_type="thinking",
      source_message_id="src-1",
    )
    assert msg.tag_type == TagType.THINKING

  def test_attributes_copied_not_aliased(self):
    src = {"k": "v"}
    msg = Message(role=MessageRole.UTILITY, content="x", attributes=src)
    src["k"] = "mutated"
    assert msg.attributes == {"k": "v"}


########################################################################
#                       SERIALIZATION ROUND-TRIP                       #
########################################################################
class TestMessageSerialization:
  def test_utility_message_round_trip(self):
    original = Message(
      role=MessageRole.UTILITY,
      content='{"name":"echo"}',
      tag_type=TagType.TOOL,
      source_message_id="src-1",
      start_index=10,
      end_index=42,
      attributes={"name": "echo"},
    )
    data = original.to_dict()
    restored = Message.from_dict(data)
    assert restored.role == MessageRole.UTILITY
    assert restored.tag_type == TagType.TOOL
    assert restored.source_message_id == "src-1"
    assert restored.start_index == 10
    assert restored.end_index == 42
    assert restored.attributes == {"name": "echo"}
    assert restored.content == original.content
    assert restored.message_id == original.message_id

  def test_to_dict_omits_unset_utility_fields(self):
    """Non-utility messages serialize without the new optional fields."""
    msg = Message(role=MessageRole.USER, content="hello")
    data = msg.to_dict()
    for key in (
      "tag_type",
      "source_message_id",
      "start_index",
      "end_index",
      "attributes",
    ):
      assert key not in data, f"unexpected utility field in user-message dict: {key}"

  def test_to_dict_serializes_tag_type_value(self):
    msg = Message(
      role=MessageRole.UTILITY,
      content="x",
      tag_type=TagType.REFERENCE,
    )
    data = msg.to_dict()
    assert data["tag_type"] == "reference"

  def test_to_dict_omits_empty_attributes(self):
    msg = Message(
      role=MessageRole.UTILITY,
      content="x",
      tag_type=TagType.TOOL,
      attributes={},
    )
    data = msg.to_dict()
    assert "attributes" not in data

  def test_minimal_payload_round_trip(self):
    """A content-only dict hydrates a TextArtifact and re-serializes
    without optional utility fields."""
    payload = {
      "message_id": "msg-1",
      "parent_id": None,
      "role": "user",
      "content": "hello",
      "created_at": 1.0,
      "updated_at": 1.0,
    }
    msg = Message.from_dict(payload)
    assert msg.tag_type is None
    assert msg.source_message_id is None
    assert msg.start_index is None
    assert msg.end_index is None
    assert msg.attributes == {}
    assert msg.content == "hello"
    data = msg.to_dict()
    assert data["message_id"] == "msg-1"
    assert data["role"] == "user"
    assert "content" not in data
    assert "file_ids" not in data
    assert "tag_type" not in data
    assert "artifacts" in data
    assert len(data["artifacts"]) == 1
    assert data["artifacts"][0]["content"] == "hello"

  def test_from_dict_accepts_leftover_speaker_key(self):
    msg = Message.from_dict({
      "message_id": "msg-1",
      "parent_id": None,
      "speaker": "assistant",
      "content": "hi",
    })
    assert msg.role == MessageRole.ASSISTANT
    assert "speaker" not in msg.to_dict()


########################################################################
#                       CONVERSATION APPEND_UTILITY                    #
########################################################################
class TestConversationAppendUtility:
  def test_append_utility_creates_message_and_advances_head(self):
    conv = Conversation(title="t")
    assistant = conv.add_message(MessageRole.ASSISTANT, "running tool")
    utility = conv.append_utility(
      tag_type=TagType.TOOL,
      content='{"name":"echo","parameters":{}}',
      source_message_id=assistant.message_id,
      start_index=0,
      end_index=20,
    )
    assert utility.role == MessageRole.UTILITY
    assert utility.tag_type == TagType.TOOL
    assert utility.source_message_id == assistant.message_id
    # Stored inline and is now the active head; chained as a child of
    # the previous head by default.
    assert utility in conv.messages
    assert conv.active_head_id == utility.message_id
    assert utility.parent_id == assistant.message_id

  def test_append_utility_emits_message_created_event(self):
    captured = []

    def on_event(event, message):
      captured.append((event, message))

    conv = Conversation(title="t", on_event=on_event)
    assistant = conv.add_message(MessageRole.ASSISTANT, "x")
    captured.clear()

    utility = conv.append_utility(
      tag_type=TagType.TOOL,
      content="payload",
      source_message_id=assistant.message_id,
      start_index=0,
      end_index=7,
      attributes={"name": "echo"},
    )

    types = [e.event_type for e, _ in captured]
    assert EventType.MESSAGE_CREATED in types
    created_event, observed_msg = next(
      (e, m) for e, m in captured if e.event_type == EventType.MESSAGE_CREATED
    )
    assert observed_msg is utility
    assert created_event.metadata["tag_type"] == TagType.TOOL.value
    assert created_event.metadata["source_message_id"] == assistant.message_id
    assert created_event.metadata["start_index"] == 0
    assert created_event.metadata["end_index"] == 7
    assert created_event.metadata["attribute_count"] == 1

  def test_append_utility_explicit_parent_id_overrides_default(self):
    conv = Conversation(title="t")
    user_a = conv.add_message(MessageRole.USER, "hi")
    assistant = conv.add_message(MessageRole.ASSISTANT, "answer")
    # Pretend the streaming has already advanced past the assistant
    # message to a later turn; we still want the utility to attach
    # behind the original user message.
    utility = conv.append_utility(
      tag_type=TagType.THINKING,
      content="quietly thinking",
      source_message_id=assistant.message_id,
      parent_id=user_a.message_id,
    )
    assert utility.parent_id == user_a.message_id
    # ``source_message_id`` is independent of ``parent_id``.
    assert utility.source_message_id == assistant.message_id

  def test_append_utility_preserves_json_content(self):
    conv = Conversation(title="t")
    assistant = conv.add_message(MessageRole.ASSISTANT, "running tool")
    utility = conv.append_utility(
      tag_type=TagType.TOOL,
      content='{"name":"echo","parameters":{"x":1}}',
      source_message_id=assistant.message_id,
    )
    assert utility.content == '{"name":"echo","parameters":{"x":1}}'


########################################################################
#                       LINEARIZATION FILTERING                        #
########################################################################
class TestConversationLinearization:
  def _seed(self):
    conv = Conversation(title="t")
    user = conv.add_message(MessageRole.USER, "do the thing")
    assistant = conv.add_message(MessageRole.ASSISTANT, "ok, calling tool")
    utility = conv.append_utility(
      tag_type=TagType.TOOL,
      content='{"name":"echo"}',
      source_message_id=assistant.message_id,
      start_index=0,
      end_index=15,
    )
    follow_up = conv.add_message(MessageRole.ASSISTANT, "tool was called")
    return conv, user, assistant, utility, follow_up

  def test_get_thread_filters_utility_by_default(self):
    conv, user, assistant, utility, follow_up = self._seed()
    thread = conv.get_thread()
    assert utility not in thread
    ids = [m.message_id for m in thread]
    assert ids == [user.message_id, assistant.message_id, follow_up.message_id]

  def test_get_thread_includes_utility_when_requested(self):
    conv, user, assistant, utility, follow_up = self._seed()
    thread = conv.get_thread(include_utility=True)
    ids = [m.message_id for m in thread]
    assert ids == [
      user.message_id,
      assistant.message_id,
      utility.message_id,
      follow_up.message_id,
    ]

  def test_get_messages_filters_utility_by_default(self):
    conv, _, _, utility, _ = self._seed()
    visible = conv.get_messages()
    assert utility not in visible

  def test_get_messages_include_utility_flag(self):
    conv, _, _, utility, _ = self._seed()
    visible = conv.get_messages(include_utility=True)
    assert utility in visible

  def test_get_messages_explicit_utility_role_returns_utility(self):
    """Asking for ``MessageRole.UTILITY`` explicitly returns utility
    messages even when ``include_utility`` defaults to False."""
    conv, _, _, utility, _ = self._seed()
    only_utility = conv.get_messages(role=MessageRole.UTILITY)
    assert only_utility == [utility]

  def test_messages_list_preserves_utility(self):
    """The flat ``self.messages`` list always contains every message
    regardless of linearization filtering."""
    conv, _, _, utility, _ = self._seed()
    assert utility in conv.messages


########################################################################
#                  CONVERSATION ROUND-TRIP WITH UTILITIES              #
########################################################################
class TestConversationRoundTrip:
  def test_to_dict_from_dict_preserves_utility_messages(self):
    conv = Conversation(title="round-trip")
    user = conv.add_message(MessageRole.USER, "hi")
    assistant = conv.add_message(MessageRole.ASSISTANT, "hello")
    conv.append_utility(
      tag_type=TagType.THINKING,
      content="(considering)",
      source_message_id=assistant.message_id,
      start_index=2,
      end_index=20,
      attributes={"depth": "shallow"},
    )

    data = conv.to_dict()
    restored = Conversation.from_dict(data)

    assert len(restored.messages) == len(conv.messages)
    util_pairs = [
      (orig, rest)
      for orig, rest in zip(conv.messages, restored.messages)
      if orig.role == MessageRole.UTILITY
    ]
    assert len(util_pairs) == 1
    orig_util, rest_util = util_pairs[0]
    assert rest_util.tag_type == orig_util.tag_type == TagType.THINKING
    assert rest_util.source_message_id == orig_util.source_message_id
    assert rest_util.start_index == orig_util.start_index
    assert rest_util.end_index == orig_util.end_index
    assert rest_util.attributes == orig_util.attributes
    assert rest_util.content == orig_util.content

  def test_plain_conversation_round_trip(self):
    """A conversation with no utility messages round-trips without
    growing utility-only fields on messages."""
    conv = Conversation(title="plain")
    conv.add_message(MessageRole.USER, "hi")
    conv.add_message(MessageRole.ASSISTANT, "hello")
    data = conv.to_dict()
    for m in data["messages"]:
      assert "tag_type" not in m
      assert "source_message_id" not in m
      assert "start_index" not in m
      assert "end_index" not in m
      assert "attributes" not in m
      assert "file_ids" not in m
      assert "artifacts" in m
    restored = Conversation.from_dict(data)
    assert [m.role for m in restored.messages] == [
      MessageRole.USER,
      MessageRole.ASSISTANT,
    ]
