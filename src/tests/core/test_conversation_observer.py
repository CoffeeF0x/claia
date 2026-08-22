"""
Tests for the Conversation observer and streaming API.
"""

import pytest

from claia.core.data import Conversation, EventType
from claia.core.enums.conversation import MessageRole


def _capture_observer():
  events = []

  def _on_event(event, message):
    events.append((event.event_type, message))

  return _on_event, events


def test_observer_invoked_on_add_message():
  on_event, captured = _capture_observer()
  conv = Conversation(title="t", on_event=on_event)
  msg = conv.add_message(MessageRole.USER, "hi")

  types = [t for t, _ in captured]
  assert EventType.CONVERSATION_CREATED in types
  assert EventType.MESSAGE_CREATED in types
  created_entry = next(e for e in captured if e[0] == EventType.MESSAGE_CREATED)
  assert created_entry[1] is msg


def test_observe_replaces_callback_and_pull_events_still_drains():
  on_event, captured = _capture_observer()
  conv = Conversation(title="t")
  conv.observe(on_event)
  conv.add_message(MessageRole.USER, "hi")

  assert any(t == EventType.MESSAGE_CREATED for t, _ in captured)
  pending = conv.pull_events()
  assert any(e.event_type == EventType.MESSAGE_CREATED for e in pending)
  assert conv.peek_events() == []


def test_observer_failure_is_isolated():
  def boom(event, message):
    raise RuntimeError("observer broke")

  conv = Conversation(title="t", on_event=boom)
  msg = conv.add_message(MessageRole.USER, "hi")
  assert msg.message_id in {m.message_id for m in conv.messages}


def test_streaming_methods_emit_start_and_end_only():
  on_event, captured = _capture_observer()
  conv = Conversation(title="t", on_event=on_event)
  captured.clear()

  msg = conv.start_streaming_message(MessageRole.ASSISTANT)
  conv.append_stream_chunk(msg.message_id, "hello ")
  conv.append_stream_chunk(msg.message_id, "world")
  conv.end_streaming_message(msg.message_id)

  types = [t for t, _ in captured]
  assert types == [EventType.MESSAGE_STREAM_START, EventType.MESSAGE_STREAM_END]
  assert msg.content == "hello world"


def test_end_streaming_message_with_error_attaches_error_metadata():
  conv = Conversation(title="t")
  msg = conv.start_streaming_message(MessageRole.ASSISTANT)
  conv.append_stream_chunk(msg.message_id, "partial")
  conv.end_streaming_message(msg.message_id, error="boom")

  end_event = next(
    e for e in conv.events if e.event_type == EventType.MESSAGE_STREAM_END
  )
  assert end_event.metadata.get("error") == "boom"


def test_delete_message_provides_pre_deletion_snapshot():
  on_event, captured = _capture_observer()
  conv = Conversation(title="t", on_event=on_event)
  msg = conv.add_message(MessageRole.USER, "hi")
  captured.clear()

  conv.delete_message(msg.message_id)

  assert len(captured) == 1
  evt_type, observed_msg = captured[0]
  assert evt_type == EventType.MESSAGE_DELETED
  assert observed_msg.message_id == msg.message_id
