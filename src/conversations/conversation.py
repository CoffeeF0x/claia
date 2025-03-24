"""
This module contains the conversation functionality for CLAIA.
It defines classes for managing conversations with LLMs.
"""

# External dependencies
import os
import time
import uuid
import json
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field

# Internal dependencies
from .base import BaseFile
from .files import FileFactory, TextFile, ImageFile, AudioFile, VideoFile, DocumentFile, GenericFile
from enums import MessageRole, ActionType



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                              CONSTANTS                               #
########################################################################
DEFAULT_SYSTEM_PROMPT = """You are CLAIA, a helpful AI assistant.
Answer the user's questions to the best of your ability."""



########################################################################
#                           MESSAGE CLASSES                            #
########################################################################
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
  file_ids: List[str] = field(default_factory=list)

  def to_dict(self) -> Dict[str, Any]:
    """
    Convert the message to a dictionary representation.

    Returns:
        Dict[str, Any]: The message as a dictionary
    """
    return {
      "id": self.id,
      "role": self.role.value,
      "content": self.content,
      "timestamp": self.timestamp,
      "metadata": self.metadata,
      "file_ids": self.file_ids
    }

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> 'Message':
    """
    Create a message from a dictionary representation.

    Args:
        data: The dictionary containing the message data

    Returns:
        Message: The created message
    """
    return cls(
      id=data.get("id", str(uuid.uuid4())),
      role=MessageRole(data["role"]),
      content=data["content"],
      timestamp=data.get("timestamp", time.time()),
      metadata=data.get("metadata", {}),
      file_ids=data.get("file_ids", [])
    )



########################################################################
#                          CONVERSATION CLASS                          #
########################################################################
class Conversation(BaseFile):
  """
  Represents a conversation with an LLM.

  A conversation contains messages, system prompts, and file references.
  """

  def __init__(self,
               base_directory: str,
               files_directory: str,
               conversation_id: Optional[str] = None,
               title: str = "New Conversation",
               system_prompt: Optional[str] = None):
    """
    Initialize a Conversation object.

    Args:
        base_directory: The base directory for conversation storage
        files_directory: The directory for storing files
        conversation_id: Optional ID for the conversation
        title: Optional title for the conversation
        system_prompt: Optional system prompt for the conversation
    """
    # Initialize with a dummy file path that will be set properly when saved
    dummy_path = os.path.join(base_directory, conversation_id or str(uuid.uuid4()))
    super().__init__(file_path=dummy_path, base_directory=base_directory)

    self.conversation_id = conversation_id or self.file_id
    self.title = title
    self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
    self.files_directory = files_directory
    self.messages: List[Message] = []

    # Add the system message if provided
    if self.system_prompt:
      self.add_message(MessageRole.SYSTEM, self.system_prompt)

  def add_message(self,
                 role: MessageRole,
                 content: str,
                 metadata: Optional[Dict[str, Any]] = None,
                 file_paths: Optional[List[str]] = None) -> Message:
    """
    Add a message to the conversation.

    Args:
        role: The role of the message sender
        content: The content of the message
        metadata: Optional metadata for the message
        file_paths: Optional list of file paths to attach to the message

    Returns:
        Message: The created message
    """
    message = Message(
      role=role,
      content=content,
      metadata=metadata or {}
    )

    # Add files if provided
    if file_paths:
      for file_path in file_paths:
        file_id = self.add_file(file_path)
        if file_id:
          message.file_ids.append(file_id)

    self.messages.append(message)
    return message

  def add_file(self, file_path: str) -> Optional[str]:
    """
    Add a file to the conversation.

    Args:
        file_path: The path to the file to add

    Returns:
        Optional[str]: The ID of the added file, or None if adding failed
    """
    try:
      if not os.path.exists(file_path):
        logger.warning(f"File {file_path} does not exist")
        return None

      # Create the appropriate file object based on the file type
      file = FileFactory.create_file(file_path, self.files_directory)

      # Process the file to extract metadata
      file.process()

      # Save the file to the files directory
      if file.save():
        return file.file_id

      return None
    except Exception as e:
      logger.error(f"Failed to add file {file_path}: {e}")
      return None

  def get_file(self, file_id: str) -> Optional[Union[TextFile, ImageFile, AudioFile, VideoFile, DocumentFile, GenericFile]]:
    """
    Get a file from the conversation by its ID.

    Args:
        file_id: The ID of the file to get

    Returns:
        Optional[Union[TextFile, ImageFile, AudioFile, VideoFile, DocumentFile, GenericFile]]:
            The file, or None if not found
    """
    return FileFactory.load_file(file_id, self.files_directory)

  def get_messages(self) -> List[Message]:
    """
    Get all messages in the conversation.

    Returns:
        List[Message]: The messages in the conversation
    """
    return self.messages

  def update_system_prompt_if_empty(self, system_prompt: str) -> None:
    """
    Update the system prompt if it's empty or not set.

    This method will update the system prompt and add a system message
    if there are no existing system messages in the conversation.

    Args:
        system_prompt: The system prompt to set
    """
    # Check if we have any system messages
    has_system_message = any(message.role == MessageRole.SYSTEM for message in self.messages)

    # If no system message exists, update the system prompt and add a system message
    if not has_system_message:
      self.system_prompt = system_prompt
      # Add the system message at the beginning of the conversation
      system_message = Message(role=MessageRole.SYSTEM, content=system_prompt)
      self.messages.insert(0, system_message)
      logger.debug(f"Added system message: {system_prompt[:50]}{'...' if len(system_prompt) > 50 else ''}")

  def update_system_prompt(self, system_prompt: str) -> None:
    """
    Update the system prompt and any existing system messages.

    This method will update the system prompt and either update an existing
    system message or add a new one if none exists.

    Args:
        system_prompt: The system prompt to set
    """
    # Update the system prompt property
    self.system_prompt = system_prompt

    # Check if we have any system messages
    system_message_found = False

    # Update any existing system messages
    for message in self.messages:
      if message.role == MessageRole.SYSTEM:
        message.content = system_prompt
        system_message_found = True
        logger.debug(f"Updated system message: {system_prompt[:50]}{'...' if len(system_prompt) > 50 else ''}")

    # If no system message exists, add one at the beginning
    if not system_message_found:
      system_message = Message(role=MessageRole.SYSTEM, content=system_prompt)
      self.messages.insert(0, system_message)
      logger.debug(f"Added system message: {system_prompt[:50]}{'...' if len(system_prompt) > 50 else ''}")

  def get_formatted_messages(self) -> List[Dict[str, Any]]:
    """
    Get the messages in a format suitable for sending to an LLM.

    Returns:
        List[Dict[str, Any]]: The formatted messages
    """
    formatted_messages = []

    for message in self.messages:
      formatted_message = {
        "role": message.role.value,
        "content": message.content
      }

      # Add file contents for supported file types
      if message.file_ids:
        file_contents = []
        for file_id in message.file_ids:
          file = self.get_file(file_id)
          if file:
            if isinstance(file, TextFile):
              file_contents.append(f"File: {file.file_name}\n\n{file.get_preview()}")
            elif isinstance(file, ImageFile):
              # For images, we might include a base64 representation
              # or just a placeholder depending on the LLM's capabilities
              file_contents.append(f"[Image: {file.file_name}]")
            else:
              file_contents.append(file.get_preview())

        if file_contents:
          formatted_message["content"] += "\n\n" + "\n\n".join(file_contents)

      formatted_messages.append(formatted_message)

    return formatted_messages

  def to_dict(self) -> Dict[str, Any]:
    """
    Convert the conversation to a dictionary.

    Returns:
        Dict[str, Any]: The conversation as a dictionary
    """
    return {
      "conversation_id": self.conversation_id,
      "title": self.title,
      "system_prompt": self.system_prompt,
      "files_directory": self.files_directory,
      "messages": [message.to_dict() for message in self.messages],
      "timestamp": self.timestamp
    }

  @classmethod
  def from_dict(cls, data: Dict[str, Any], base_directory: str, files_directory: str) -> 'Conversation':
    """
    Create a conversation from a dictionary.

    Args:
        data: The dictionary containing the conversation data
        base_directory: The base directory for conversation storage
        files_directory: The directory for storing files

    Returns:
        Conversation: The created conversation
    """
    conversation = cls(
      base_directory=base_directory,
      files_directory=files_directory,
      conversation_id=data["conversation_id"],
      title=data["title"],
      system_prompt=data.get("system_prompt")
    )

    # Clear the default system message
    conversation.messages = []

    # Add all messages from the data
    for message_data in data.get("messages", []):
      message = Message.from_dict(message_data)
      conversation.messages.append(message)

    return conversation

  def save(self) -> Optional[str]:
    """
    Save the conversation to a file.

    Returns:
        Optional[str]: The path to the saved file, or None if saving failed
    """
    try:
      # Ensure the conversations directory exists
      os.makedirs(self.base_directory, exist_ok=True)

      # Save the conversation to a JSON file
      file_path = os.path.join(self.base_directory, f"{self.conversation_id}.json")
      with open(file_path, 'w') as f:
        json.dump(self.to_dict(), f, indent=2)

      return file_path
    except Exception as e:
      logger.error(f"Failed to save conversation {self.conversation_id}: {e}")
      return None

  @classmethod
  def load(cls, conversation_id: str, base_directory: str, files_directory: str) -> Optional['Conversation']:
    """
    Load a conversation from a file.

    Args:
        conversation_id: The ID of the conversation to load
        base_directory: The base directory for conversation storage
        files_directory: The directory for storing files

    Returns:
        Optional[Conversation]: The loaded conversation, or None if loading failed
    """
    try:
      file_path = os.path.join(base_directory, f"{conversation_id}.json")

      if not os.path.exists(file_path):
        logger.error(f"Conversation file {file_path} does not exist")
        return None

      with open(file_path, 'r') as f:
        data = json.load(f)

      return cls.from_dict(data, base_directory, files_directory)
    except Exception as e:
      logger.error(f"Failed to load conversation {conversation_id}: {e}")
      return None

  @classmethod
  def list_conversations(cls, base_directory: str) -> List[Dict[str, Any]]:
    """
    List all conversations in the base directory.

    Args:
        base_directory: The base directory for conversation storage

    Returns:
        List[Dict[str, Any]]: A list of conversation metadata
    """
    try:
      if not os.path.exists(base_directory):
        logger.warning(f"Conversations directory {base_directory} does not exist")
        return []

      conversation_files = [f for f in os.listdir(base_directory) if f.endswith('.json')]
      conversations = []

      for file_name in conversation_files:
        try:
          file_path = os.path.join(base_directory, file_name)
          with open(file_path, 'r') as f:
            data = json.load(f)

          conversations.append({
            "conversation_id": data["conversation_id"],
            "title": data["title"],
            "timestamp": data.get("timestamp", 0),
            "message_count": len(data.get("messages", []))
          })
        except Exception as e:
          logger.error(f"Failed to read conversation file {file_name}: {e}")

      # Sort by timestamp, newest first
      conversations.sort(key=lambda x: x["timestamp"], reverse=True)

      return conversations
    except Exception as e:
      logger.error(f"Failed to list conversations: {e}")
      return []