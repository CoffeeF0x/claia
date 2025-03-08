"""
This module contains commands for managing conversations.
"""

# External dependencies
import os
import json

# Internal dependencies
from commands.base import Command, command
from errors import Result
from conversations import Conversation, MessageRole
from settings import Settings



##################################################
#                 COMMAND CLASS                  #
##################################################
class ConversationCommand(Command):

  @command(
    path=["list"],
    description="List any saved conversations",
    help_text="List any saved conversations"
  )
  def list_conversations(self, settings: Settings) -> str:
    """List all conversations"""
    conversations = Conversation.list_conversations(settings.conversation_directory)
    if not conversations:
      return "No saved conversations found"

    output = []
    for conv in conversations:
      line = f"{conv['id']}: {conv['title']} ({conv['message_count']} messages)"
      print(line)
      output.append(line)
    return "\n".join(output)

  @command(
    path=["load"],
    description="Load a saved conversation",
    help_text="Load a saved conversation",
    parameters={
      "type": "object",
      "properties": {
        "conversation_id": {
          "type": "string",
          "description": "ID of the conversation to load"
        }
      },
      "required": ["conversation_id"]
    }
  )
  def load_conversation(self, settings: Settings, conversation_id: str) -> str:
    """Load a stored conversation"""
    filepath = os.path.join(settings.conversation_directory, f"{conversation_id}.json")
    if os.path.exists(filepath):
      settings.active_conversation = Conversation.load(filepath)
      message = f"Loaded conversation: {settings.active_conversation.title}"
      print(message)
      return message
    else:
      message = "Conversation not found"
      print(message)
      return message

  @command(
    path=["new"],
    description="Start a new conversation",
    help_text="Start a new conversation"
  )
  def new_conversation(self, settings: Settings) -> str:
    """Create a new conversation"""
    title = "New Conversation"
    # title = input("Enter a title for the new conversation: ")

    # Create new conversation with system prompt if available
    system_prompt = settings.active_prompt.prompt if settings.active_prompt else None
    new_conversation = Conversation(title=title, system_prompt=system_prompt)

    # Save the conversation
    new_conversation.save(settings.conversation_directory)
    settings.active_conversation = new_conversation

    message = f"Created new conversation: {title} (ID: {new_conversation.id})"
    print(message)
    print("This is now the active conversation.")
    return message

  @command(
    path=["print"],
    description="Display the current conversation or a specific conversation",
    help_text="Display the current conversation or a specific conversation",
    parameters={
      "type": "object",
      "properties": {
        "conversation_id": {
          "type": "string",
          "description": "Optional ID of a specific conversation to display"
        }
      }
    }
  )
  def print_conversation(self, settings: Settings, conversation_id: str = None) -> str:
    """Print the current conversation or a specific conversation"""
    if conversation_id:
      filepath = os.path.join(settings.conversation_directory, f"{conversation_id}.json")
      if os.path.exists(filepath):
        conversation = Conversation.load(filepath)
      else:
        message = f"Conversation with ID {conversation_id} not found"
        print(message)
        return message
    elif settings.active_conversation:
      conversation = settings.active_conversation
    else:
      message = "No active conversation selected"
      print(message)
      return message

    print(f"\nConversation: {conversation.title}")
    output = [f"Conversation: {conversation.title}"]

    for message in conversation.get_messages():
      print(f"\n##### SOURCE: {message.role.value}")
      print(message.content)
      output.append(f"##### SOURCE: {message.role.value}")
      output.append(message.content)

    return "\n".join(output)
