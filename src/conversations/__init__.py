"""
This module contains the conversation model for CLAIA.
It defines the structure and operations for managing conversations between users and agents.
"""

# External dependencies
import uuid
import json
import os
import time
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

# Internal dependencies
from conversations.files import FileReference, FileHandler
from conversations.artifacts import Artifact
from conversations.prompts import Prompt



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
  FILE = "file"
  IMAGE = "image"
  AUDIO = "audio"
  MODEL_3D = "model-3d"
  ARTIFACT = "artifact"



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
  timestamp: float = field(default_factory=lambda: time.time())
  metadata: Dict[str, Any] = field(default_factory=dict)
  file_references: List[FileReference] = field(default_factory=list)
  artifact_references: List[str] = field(default_factory=list)

  def to_dict(self) -> Dict[str, Any]:
    """Convert the message to a dictionary representation."""
    return {
      "id": self.id,
      "role": self.role.value,
      "content": self.content,
      "timestamp": self.timestamp,
      "metadata": self.metadata,
      "file_references": [ref.to_dict() for ref in self.file_references],
      "artifact_references": self.artifact_references
    }

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> 'Message':
    """Create a message from a dictionary representation."""
    message = cls(
      id=data.get("id", str(uuid.uuid4())),
      role=MessageRole(data["role"]),
      content=data["content"],
      timestamp=data.get("timestamp", time.time()),
      metadata=data.get("metadata", {})
    )

    # Add file references
    for ref_data in data.get("file_references", []):
      message.file_references.append(FileReference.from_dict(ref_data))

    # Add artifact references
    message.artifact_references = data.get("artifact_references", [])

    return message

  def add_file(self, file_path: str) -> FileReference:
    """Add a file to this message."""
    file_ref = FileReference(file_path=file_path)
    self.file_references.append(file_ref)
    return file_ref

  def add_artifact_reference(self, artifact_id: str):
    """Add a reference to an artifact."""
    if artifact_id not in self.artifact_references:
      self.artifact_references.append(artifact_id)


class Conversation:
  """
  Represents a conversation between a user and an assistant.

  A conversation is a sequence of messages with metadata about the conversation.
  """
  def __init__(self,
               conversation_directory: str,
               artifacts_directory: str,
               id: Optional[str] = None,
               title: str = "New Conversation",
               system_prompt: Optional[Union[str, Prompt]] = None,
               files_subdirectory: str = "files"):
    self.id = id or str(uuid.uuid4())
    self.title = title
    self.messages: List[Message] = []
    self.metadata: Dict[str, Any] = {}
    self.created_at = time.time()
    self.updated_at = self.created_at

    # Store directory paths
    self.conversation_dir = os.path.join(conversation_directory, self.id)
    self.artifacts_directory = artifacts_directory
    self.files_directory = files_subdirectory

    # Ensure the conversation directory exists
    os.makedirs(self.conversation_dir, exist_ok=True)

    # Files directory for this conversation
    self.files_dir = os.path.join(self.conversation_dir, self.files_directory)
    os.makedirs(self.files_dir, exist_ok=True)

    # Track prompt history
    self.prompt_history: List[Dict[str, Any]] = []

    # Add system prompt if provided
    if system_prompt:
      if isinstance(system_prompt, Prompt):
        self.set_system_prompt(system_prompt)
      else:
        self.add_message(MessageRole.SYSTEM, system_prompt)

  def add_message(self,
                 role: MessageRole,
                 content: str,
                 metadata: Dict[str, Any] = None,
                 files: List[str] = None) -> Message:
    """Add a message to the conversation."""
    message = Message(role=role, content=content, metadata=metadata or {})

    # Add any files
    if files:
      for file_path in files:
        message.add_file(file_path)

    self.messages.append(message)
    self.updated_at = message.timestamp
    return message

  def get_messages(self) -> List[Message]:
    """Get all messages in the conversation."""
    return self.messages

  def set_system_prompt(self, prompt: Prompt):
    """Set or update the system prompt using a Prompt object."""
    # Record in prompt history
    self.prompt_history.append({
      "prompt_id": prompt.prompt_id,
      "timestamp": time.time(),
      "name": prompt.name,
      "title": prompt.title
    })

    # Check if there's an existing system message
    system_messages = [i for i, msg in enumerate(self.messages)
                      if msg.role == MessageRole.SYSTEM]

    if system_messages:
      # Replace the first system message
      self.messages[system_messages[0]] = Message(
        role=MessageRole.SYSTEM,
        content=prompt.prompt,
        metadata={"prompt_id": prompt.prompt_id}
      )
      # Remove any other system messages
      self.messages = [msg for i, msg in enumerate(self.messages)
                      if i == system_messages[0] or msg.role != MessageRole.SYSTEM]
    else:
      # Add a new system message at the beginning
      self.messages.insert(0, Message(
        role=MessageRole.SYSTEM,
        content=prompt.prompt,
        metadata={"prompt_id": prompt.prompt_id}
      ))

  def update_system_prompt_if_empty(self, system_prompt: str) -> bool:
    """
    Update the system prompt for this conversation.

    If the conversation has only a system message or is empty,
    it will replace/add the system message.
    If the conversation already has user or assistant messages,
    it will return False to indicate the update was not performed.

    Args:
        system_prompt: The new system prompt to set

    Returns:
        bool: True if the system prompt was updated, False otherwise
    """
    # Check if conversation has only system messages or is empty
    has_only_system = all(msg.role == MessageRole.SYSTEM for msg in self.messages)

    if not self.messages or has_only_system:
      # Remove any existing system messages
      self.messages = [msg for msg in self.messages if msg.role != MessageRole.SYSTEM]

      # Add the new system message
      self.add_message(MessageRole.SYSTEM, system_prompt)
      return True

    return False

  def get_formatted_messages(self) -> List[Dict[str, Any]]:
    """Get messages formatted for LLM API consumption."""
    formatted_messages = []

    for msg in self.messages:
      if msg.role in [MessageRole.SYSTEM, MessageRole.USER, MessageRole.ASSISTANT]:
        message_dict = {"role": msg.role.value, "content": msg.content}

        # Add file references if present
        if msg.file_references:
          file_contents = []
          for file_ref in msg.file_references:
            handler = FileHandler.get_handler_for_file(file_ref)
            preview = handler.get_preview(file_ref)
            file_contents.append(f"[File: {file_ref.file_name}]\n{preview}")

          # Append file contents to the message
          if file_contents:
            message_dict["content"] += "\n\n" + "\n\n".join(file_contents)

        formatted_messages.append(message_dict)

    return formatted_messages

  def add_file_to_message(self, message_id: str, file_path: str) -> FileReference:
    """Add a file to a specific message."""
    for msg in self.messages:
      if msg.id == message_id:
        return msg.add_file(file_path)

    raise ValueError(f"Message with ID {message_id} not found")

  def add_artifact_to_message(self,
                             message_id: str,
                             artifact: Artifact) -> None:
    """Add an artifact reference to a specific message."""
    for msg in self.messages:
      if msg.id == message_id:
        msg.add_artifact_reference(artifact.artifact_id)
        return

    raise ValueError(f"Message with ID {message_id} not found")

  def get_artifacts(self) -> List[Artifact]:
    """Get all artifacts referenced in this conversation."""
    artifact_ids = set()
    for msg in self.messages:
      artifact_ids.update(msg.artifact_references)

    artifacts = []
    for artifact_id in artifact_ids:
      try:
        artifact = Artifact.load(artifact_id, self.artifacts_directory)
        artifacts.append(artifact)
      except Exception as e:
        print(f"Error loading artifact {artifact_id}: {e}")

    return artifacts

  def to_dict(self) -> Dict[str, Any]:
    """Convert the conversation to a dictionary representation."""
    return {
      "id": self.id,
      "title": self.title,
      "messages": [msg.to_dict() for msg in self.messages],
      "metadata": self.metadata,
      "created_at": self.created_at,
      "updated_at": self.updated_at,
      "prompt_history": self.prompt_history
    }

  @classmethod
  def from_dict(cls, data: Dict[str, Any], conversation_directory: str, artifacts_directory: str,
                files_subdirectory: str = "files") -> 'Conversation':
    """Create a conversation from a dictionary representation."""
    conversation = cls(
      id=data.get("id"),
      title=data.get("title", "New Conversation"),
      conversation_directory=conversation_directory,
      artifacts_directory=artifacts_directory,
      files_subdirectory=files_subdirectory
    )
    conversation.metadata = data.get("metadata", {})
    conversation.created_at = data.get("created_at", conversation.created_at)
    conversation.updated_at = data.get("updated_at", conversation.updated_at)
    conversation.prompt_history = data.get("prompt_history", [])

    # Add messages
    for msg_data in data.get("messages", []):
      message = Message.from_dict(msg_data)
      conversation.messages.append(message)

    return conversation

  def save(self) -> str:
    """Save the conversation to a file."""
    filepath = os.path.join(self.conversation_dir, "conversation.json")

    with open(filepath, 'w') as f:
      json.dump(self.to_dict(), f, indent=2)

    return filepath

  @classmethod
  def load(cls, conversation_id: str, conversation_directory: str, artifacts_directory: str,
           files_subdirectory: str = "files") -> 'Conversation':
    """Load a conversation by ID."""
    filepath = os.path.join(conversation_directory, conversation_id, "conversation.json")

    with open(filepath, 'r') as f:
      data = json.load(f)

    return cls.from_dict(data, conversation_directory, artifacts_directory, files_subdirectory)

  @classmethod
  def list_conversations(cls, conversation_directory: str) -> List[Dict[str, Any]]:
    """List all conversations in the directory."""
    conversations = []

    if not os.path.exists(conversation_directory):
      return conversations

    for item in os.listdir(conversation_directory):
      item_path = os.path.join(conversation_directory, item)
      if os.path.isdir(item_path):
        conv_file = os.path.join(item_path, "conversation.json")
        if os.path.exists(conv_file):
          try:
            with open(conv_file, 'r') as f:
              data = json.load(f)
              conversations.append({
                "id": data.get("id"),
                "title": data.get("title", "Untitled"),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
                "message_count": len(data.get("messages", []))
              })
          except Exception as e:
            print(f"Error loading conversation {item}: {e}")

    # Sort by updated_at (newest first)
    conversations.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
    return conversations