"""
Tests for the Conversation class.
"""

# External dependencies
import pytest
import os
import json
import tempfile
import time
import uuid
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List

# Internal dependencies
from files import Conversation, BaseFile
from enums.conversation import MessageRole, ActionType
from enums import FileSubdirectory



########################################################################
#                              FIXTURES                                #
########################################################################
@pytest.fixture
def temp_dir():
  """Create a temporary directory for testing."""
  temp_path = tempfile.mkdtemp()
  yield temp_path
  # Clean up temp directory
  try:
    import shutil
    shutil.rmtree(temp_path)
  except:
    pass

@pytest.fixture
def sample_conversation_data():
  """Sample conversation data for testing."""
  return {
    "title": "Test Conversation",
    "prompt": "You are a helpful assistant.",
    "messages": [
      {
        "speaker": "user",
        "content": "Hello, how are you?",
        "message_id": str(uuid.uuid4()),
        "file_ids": [],
        "created_at": time.time(),
        "updated_at": time.time()
      },
      {
        "speaker": "assistant",
        "content": "I'm doing well, thank you for asking!",
        "message_id": str(uuid.uuid4()),
        "file_ids": [],
        "created_at": time.time(),
        "updated_at": time.time()
      }
    ],
    "actions": [
      {
        "action_type": "CREATE_CONVERSATION",
        "metadata": {"title": "Test Conversation"},
        "action_id": str(uuid.uuid4()),
        "timestamp": time.time()
      }
    ],
    "tool_definitions": [
      {
        "name": "calculator",
        "description": "Performs calculations",
        "parameters": {
          "type": "object",
          "properties": {
            "expression": {"type": "string"}
          },
          "required": ["expression"]
        },
        "tool_id": str(uuid.uuid4()),
        "created_at": time.time(),
        "updated_at": time.time()
      }
    ]
  }

@pytest.fixture
def conversation_file(temp_dir, sample_conversation_data):
  """Create a sample conversation file for testing."""
  conversation = Conversation.create_conversation(
    base_directory=temp_dir,
    title=sample_conversation_data["title"],
    prompt=sample_conversation_data["prompt"]
  )
  
  # Add messages
  for message_data in sample_conversation_data["messages"]:
    conversation.add_message(
      speaker=message_data["speaker"],
      content=message_data["content"]
    )
  
  # Add tool definitions
  for tool_data in sample_conversation_data["tool_definitions"]:
    conversation.add_tool_definition(
      name=tool_data["name"],
      description=tool_data["description"],
      parameters=tool_data["parameters"]
    )
  
  return conversation



########################################################################
#                          CONVERSATION TESTS                          #
########################################################################
def test_create_conversation(temp_dir, sample_conversation_data):
  """Test creating a conversation file."""
  conversation = Conversation.create_conversation(
    base_directory=temp_dir,
    title=sample_conversation_data["title"],
    prompt=sample_conversation_data["prompt"]
  )
  
  assert conversation is not None
  assert conversation.title == sample_conversation_data["title"]
  assert conversation.prompt == sample_conversation_data["prompt"]
  assert conversation.file_name.endswith(".json")
  assert conversation.exists()
  
  # Verify actions
  assert len(conversation.actions) == 1
  assert conversation.actions[0].action_type == ActionType.CREATE_CONVERSATION
  
  # Verify the file content
  with open(conversation.path, 'r') as f:
    content = json.load(f)
    assert content["title"] == sample_conversation_data["title"]
    assert content["prompt"] == sample_conversation_data["prompt"]


def test_add_message(conversation_file):
  """Test adding messages to a conversation."""
  # Add a new message
  message = conversation_file.add_message(
    speaker=MessageRole.USER,
    content="This is a new test message"
  )
  
  assert message is not None
  assert message.speaker == MessageRole.USER
  assert message.content == "This is a new test message"
  
  # Verify the message was added to the conversation
  assert message in conversation_file.messages
  
  # Verify an action was created
  assert any(a.action_type == ActionType.CREATE_MESSAGE for a in conversation_file.actions)


def test_load_conversation(temp_dir):
  """Test loading a conversation by ID."""
  # Create a conversation first
  conversation_title = "Test Load Conversation"
  conversation_prompt = "This is a test conversation for loading"
  
  original_conversation = Conversation.create_conversation(
    base_directory=temp_dir,
    title=conversation_title,
    prompt=conversation_prompt
  )
  
  # Add a message to the conversation
  original_conversation.add_message(
    speaker=MessageRole.USER,
    content="Hello, this is a test message"
  )
  
  # Add a tool definition
  original_conversation.add_tool_definition(
    name="test_tool",
    description="A test tool",
    parameters={"type": "object", "properties": {}}
  )
  
  # Save the conversation
  original_conversation.save()
  
  # Create the messages and actions lists from the original conversation
  messages_dicts = [m.to_dict() for m in original_conversation.messages]
  actions_dicts = [a.to_dict() for a in original_conversation.actions]
  tool_defs_dicts = [t.to_dict() for t in original_conversation.tool_definitions]
  
  # Mock the base load method to return a dictionary with the expected structure
  mock_load_result = {
    "metadata": {
      "file_id": original_conversation.file_id,
      "file_name": original_conversation.file_name,
      "mime_type": "application/json",
      "timestamp": time.time(),
      "metadata": {
        "title": conversation_title,
        "message_count": len(original_conversation.messages),
        "tool_count": len(original_conversation.tool_definitions)
      }
    },
    "content": json.dumps({
      "conversation_id": original_conversation.file_id,
      "title": conversation_title,
      "prompt": conversation_prompt,
      "messages": messages_dicts,
      "actions": actions_dicts,
      "tool_definitions": tool_defs_dicts,
      "created_at": original_conversation.timestamp
    })
  }
  
  with patch.object(BaseFile, 'load', return_value=mock_load_result):
    # Test loading by ID
    loaded_conversation = Conversation.load_conversation(original_conversation.file_id, temp_dir)
    
    assert loaded_conversation is not None
    assert loaded_conversation.title == conversation_title
    assert loaded_conversation.prompt == conversation_prompt
    assert loaded_conversation.file_id == original_conversation.file_id
    assert len(loaded_conversation.messages) == len(original_conversation.messages)
    assert len(loaded_conversation.actions) == len(original_conversation.actions)
    assert len(loaded_conversation.tool_definitions) == len(original_conversation.tool_definitions)
    
    # Test loading non-existent conversation
    with patch.object(BaseFile, 'load', return_value=None):
      not_found = Conversation.load_conversation("nonexistent-id", temp_dir)
      assert not_found is None
      
    # Test with JSON parsing error
    invalid_load_result = mock_load_result.copy()
    invalid_load_result["content"] = "invalid json"
    with patch.object(BaseFile, 'load', return_value=invalid_load_result):
      invalid_json = Conversation.load_conversation(original_conversation.file_id, temp_dir)
      assert invalid_json is None 