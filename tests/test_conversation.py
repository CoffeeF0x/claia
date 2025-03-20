#!/usr/bin/env python3
"""
Test script demonstrating how to use the refactored CLAIA conversation system.
"""

# External dependencies
import os
import sys
import logging
from typing import Optional

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# Internal dependencies
from conversations import Conversation
from conversations.files import FileFactory, TextFile, ImageFile
from enums import MessageRole


########################################################################
#                            INITIALIZATION                            #
########################################################################
# Set up logging
logging.basicConfig(
  level=logging.INFO,
  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define base directories
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
FILES_DIR = os.path.join(BASE_DIR, 'files')

# Ensure directories exist
os.makedirs(BASE_DIR, exist_ok=True)
os.makedirs(FILES_DIR, exist_ok=True)



########################################################################
#                              FUNCTIONS                               #
########################################################################
def create_new_conversation() -> Conversation:
  """
  Create a new conversation.

  Returns:
      Conversation: The created conversation
  """
  conversation = Conversation(
    base_directory=BASE_DIR,
    files_directory=FILES_DIR,
    title="Test Conversation"
  )

  # Add a user message
  conversation.add_message(
    role=MessageRole.USER,
    content="Hello! Can you help me understand how this system works?"
  )

  # Add an assistant message
  conversation.add_message(
    role=MessageRole.ASSISTANT,
    content="Of course! This is a simplified conversation system. "
            "You can add messages, attach files, and save/load conversations. "
            "What would you like to know more about?"
  )

  # Save the conversation
  conversation.save()
  logger.info(f"Created new conversation with ID: {conversation.conversation_id}")

  return conversation


def add_file_to_conversation(conversation: Conversation, file_path: str) -> Optional[str]:
  """
  Add a file to a conversation.

  Args:
      conversation: The conversation to add the file to
      file_path: The path to the file to add

  Returns:
      Optional[str]: The ID of the added file, or None if adding failed
  """
  # Add a message with the file
  message = conversation.add_message(
    role=MessageRole.USER,
    content="I'm attaching a file for reference.",
    file_paths=[file_path]
  )

  if not message.file_ids:
    logger.error(f"Failed to add file {file_path} to conversation")
    return None

  file_id = message.file_ids[0]
  logger.info(f"Added file with ID: {file_id}")

  # Save the conversation
  conversation.save()

  return file_id


def load_conversation(conversation_id: str) -> Optional[Conversation]:
  """
  Load a conversation by ID.

  Args:
      conversation_id: The ID of the conversation to load

  Returns:
      Optional[Conversation]: The loaded conversation, or None if loading failed
  """
  conversation = Conversation.load(
    conversation_id=conversation_id,
    base_directory=BASE_DIR,
    files_directory=FILES_DIR
  )

  if not conversation:
    logger.error(f"Failed to load conversation {conversation_id}")
    return None

  logger.info(f"Loaded conversation: {conversation.title}")
  return conversation


def list_all_conversations():
  """
  List all conversations.
  """
  conversations = Conversation.list_conversations(BASE_DIR)

  if not conversations:
    logger.info("No conversations found")
    return

  logger.info(f"Found {len(conversations)} conversations:")
  for i, conv in enumerate(conversations, 1):
    logger.info(f"{i}. {conv['title']} (ID: {conv['conversation_id']}, Messages: {conv['message_count']})")


def create_sample_text_file(content: str) -> str:
  """
  Create a sample text file.

  Args:
      content: The content to write to the file

  Returns:
      str: The path to the created file
  """
  file_path = os.path.join(os.path.dirname(__file__), 'sample.txt')

  with open(file_path, 'w') as f:
    f.write(content)

  logger.info(f"Created sample text file: {file_path}")
  return file_path



########################################################################
#                             MAIN FUNCTION                            #
########################################################################
def test_conversation_system():
  """
  Test function demonstrating the conversation system.
  """
  # Create a sample text file
  sample_file = create_sample_text_file(
    "This is a sample text file.\n"
    "It contains some text that will be processed by the system.\n"
    "The system will extract metadata like character count and line count."
  )

  # Create a new conversation
  conversation = create_new_conversation()

  # Add the sample file to the conversation
  file_id = add_file_to_conversation(conversation, sample_file)

  if file_id:
    # Get the file from the conversation
    file = conversation.get_file(file_id)

    if file and isinstance(file, TextFile):
      logger.info(f"File content preview: {file.get_preview(max_length=50)}...")
      logger.info(f"File metadata: {file.metadata}")

  # List all conversations
  list_all_conversations()

  # Load the conversation
  loaded_conversation = load_conversation(conversation.conversation_id)

  if loaded_conversation:
    # Get formatted messages for LLM
    formatted_messages = loaded_conversation.get_formatted_messages()
    logger.info(f"Formatted messages for LLM: {formatted_messages}")

  # Clean up
  os.remove(sample_file)
  logger.info("Test completed successfully")


if __name__ == "__main__":
  test_conversation_system()