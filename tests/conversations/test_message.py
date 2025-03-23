#####################
# EXTERNAL IMPORTS #
#####################
import pytest


#####################
# INTERNAL IMPORTS #
#####################
from src.conversations.message import Message


#####################
#      TESTS       #
#####################

def test_message_creation():
  """Test that a message can be created with basic attributes."""
  message = Message(
    role="user",
    content="Test message"
  )

  assert message.role == "user"
  assert message.content == "Test message"

def test_message_from_dict():
  """Test that a message can be created from a dictionary."""
  data = {
    "role": "assistant",
    "content": "Hello there!",
    "metadata": {
      "timestamp": "2024-03-21T12:00:00Z"
    }
  }

  message = Message.from_dict(data)

  assert message.role == "assistant"
  assert message.content == "Hello there!"
  assert message.metadata["timestamp"] == "2024-03-21T12:00:00Z"

def test_message_to_dict():
  """Test that a message can be converted to a dictionary."""
  message = Message(
    role="system",
    content="System message",
    metadata={"key": "value"}
  )

  result = message.to_dict()

  assert isinstance(result, dict)
  assert result["role"] == "system"
  assert result["content"] == "System message"
  assert result["metadata"]["key"] == "value"