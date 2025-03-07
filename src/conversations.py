"""
This module contains the conversation model for CLAIA.
It defines the structure and operations for managing conversations between users and agents.
"""

# External dependencies
import uuid
import json
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum



##################################################
#                     ENUMS                      #
##################################################
class MessageRole(Enum):
  """Roles for conversation messages."""
  SYSTEM = "system"
  USER = "user"
  ASSISTANT = "assistant"
  TOOL = "tool"
  TOOL_CALL = "tool-call"



##################################################
#                    CLASSES                     #
##################################################
@dataclass
class Message:
  """
  Represents a message in a conversation.

  A message contains content and metadata about who sent it and when.
  """
  role: MessageRole
  content: str
  id: str = field(default_factory=lambda: str(uuid.uuid4()))
  timestamp: float = field(default_factory=lambda: __import__('time').time())
  metadata: Dict[str, Any] = field(default_factory=dict)

  def to_dict(self) -> Dict[str, Any]:
    """Convert the message to a dictionary representation."""
    return {
      "id": self.id,
      "role": self.role.value,
      "content": self.content,
      "timestamp": self.timestamp,
      "metadata": self.metadata
    }

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> 'Message':
    """Create a message from a dictionary representation."""
    return cls(
      id=data.get("id", str(uuid.uuid4())),
      role=MessageRole(data["role"]),
      content=data["content"],
      timestamp=data.get("timestamp", __import__('time').time()),
      metadata=data.get("metadata", {})
    )


class Conversation:
  """
  Represents a conversation between a user and an assistant.

  A conversation is a sequence of messages with metadata about the conversation.
  """
  def __init__(self,
               id: Optional[str] = None,
               title: str = "New Conversation",
               system_prompt: Optional[str] = None):
    self.id = id or str(uuid.uuid4())
    self.title = title
    self.messages: List[Message] = []
    self.metadata: Dict[str, Any] = {}
    self.created_at = __import__('time').time()
    self.updated_at = self.created_at

    # Add system prompt if provided
    if system_prompt:
      self.add_message(MessageRole.SYSTEM, system_prompt)

  def add_message(self, role: MessageRole, content: str, metadata: Dict[str, Any] = None) -> Message:
    """Add a message to the conversation."""
    message = Message(role=role, content=content, metadata=metadata or {})
    self.messages.append(message)
    self.updated_at = message.timestamp
    return message

  def get_messages(self) -> List[Message]:
    """Get all messages in the conversation."""
    return self.messages

  def get_formatted_messages(self) -> List[Dict[str, Any]]:
    """Get messages formatted for LLM API consumption."""
    return [
      {"role": msg.role.value, "content": msg.content}
      for msg in self.messages
      if msg.role in [MessageRole.SYSTEM, MessageRole.USER, MessageRole.ASSISTANT]
    ]

  def to_dict(self) -> Dict[str, Any]:
    """Convert the conversation to a dictionary representation."""
    return {
      "id": self.id,
      "title": self.title,
      "messages": [msg.to_dict() for msg in self.messages],
      "metadata": self.metadata,
      "created_at": self.created_at,
      "updated_at": self.updated_at
    }

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> 'Conversation':
    """Create a conversation from a dictionary representation."""
    conversation = cls(
      id=data.get("id"),
      title=data.get("title", "New Conversation")
    )
    conversation.metadata = data.get("metadata", {})
    conversation.created_at = data.get("created_at", conversation.created_at)
    conversation.updated_at = data.get("updated_at", conversation.updated_at)

    # Add messages
    for msg_data in data.get("messages", []):
      message = Message.from_dict(msg_data)
      conversation.messages.append(message)

    return conversation

  def save(self, directory: str) -> str:
    """Save the conversation to a file."""
    os.makedirs(directory, exist_ok=True)
    filename = f"{self.id}.json"
    filepath = os.path.join(directory, filename)

    with open(filepath, 'w') as f:
      json.dump(self.to_dict(), f, indent=2)

    return filepath

  @classmethod
  def load(cls, filepath: str) -> 'Conversation':
    """Load a conversation from a file."""
    with open(filepath, 'r') as f:
      data = json.load(f)

    return cls.from_dict(data)

  @classmethod
  def list_conversations(cls, directory: str) -> List[Dict[str, Any]]:
    """List all conversations in the directory."""
    conversations = []

    if not os.path.exists(directory):
      return conversations

    for filename in os.listdir(directory):
      if filename.endswith('.json'):
        filepath = os.path.join(directory, filename)
        try:
          with open(filepath, 'r') as f:
            data = json.load(f)
            conversations.append({
              "id": data.get("id"),
              "title": data.get("title", "Untitled"),
              "created_at": data.get("created_at"),
              "updated_at": data.get("updated_at"),
              "message_count": len(data.get("messages", []))
            })
        except Exception as e:
          print(f"Error loading conversation {filename}: {e}")

    # Sort by updated_at (newest first)
    conversations.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
    return conversations