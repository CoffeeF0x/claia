#####################
# EXTERNAL IMPORTS #
#####################
import pytest
from datetime import datetime


#####################
# INTERNAL IMPORTS #
#####################
from conversations import Conversation, Message


#####################
#      TESTS       #
#####################

def test_conversation_creation(sample_conversation_json):
  """Test that a conversation can be created from JSON."""
  conversation = Conversation.from_dict(sample_conversation_json)

  assert len(conversation.messages) == 3
  assert conversation.messages[0].role == "system"
  assert conversation.messages[0].content == "You are a helpful assistant."
  assert conversation.metadata["model"] == "test-model"

def test_conversation_add_message():
  """Test that messages can be added to a conversation."""
  conversation = Conversation()

  conversation.add_message(Message(
    role="user",
    content="Test message"
  ))

  assert len(conversation.messages) == 1
  assert conversation.messages[0].role == "user"
  assert conversation.messages[0].content == "Test message"

def test_conversation_to_dict():
  """Test that a conversation can be converted to a dictionary."""
  conversation = Conversation()
  conversation.add_message(Message(
    role="user",
    content="Test message"
  ))

  result = conversation.to_dict()

  assert isinstance(result, dict)
  assert "messages" in result
  assert len(result["messages"]) == 1
  assert result["messages"][0]["role"] == "user"
  assert result["messages"][0]["content"] == "Test message"