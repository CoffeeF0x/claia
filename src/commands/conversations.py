"""
This module contains commands for managing conversations.
"""

# External dependencies
import logging

# Internal dependencies
from .base import Command, command
from results import Result
from files import Conversation
from settings import Settings
from enums import MessageRole



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                            COMMAND CLASS                             #
########################################################################
class ConversationCommand(Command):

  @command(
    path=["list"],
    description="List any saved conversations",
    help_text="List any saved conversations"
  )
  def list_conversations(self, settings: Settings) -> Result:
    """List all conversations"""
    result = Result()

    conversations = Conversation.list_conversations(settings.files_directory)
    if not conversations:
      result.message = "No saved conversations found"
      return result

    output = []
    for conv in conversations:
      line = f"{conv.get('file_id')}: {conv.get('metadata', {}).get('title', 'Untitled')} ({conv.get('metadata', {}).get('message_count', 0)} messages)"
      output.append(line)

    result.data = conversations
    result.message = "\n".join(output)
    return result

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
  def load_conversation(self, settings: Settings, conversation_id: str) -> Result:
    """Load a stored conversation"""
    result = Result()

    # Get registry from the command's registry property
    registry = self.registry if hasattr(self, 'registry') else None

    conversation = Conversation.load_conversation(
      conversation_id=conversation_id,
      base_directory=settings.files_directory,
      registry=registry
    )

    if conversation:
      settings.active_conversation = conversation
      result.data = conversation
      result.message = f"Loaded conversation: {conversation.title}"
    else:
      result = Result.fail("Conversation not found")

    return result

  @command(
    path=["new"],
    description="Start a new conversation",
    help_text="Start a new conversation"
  )
  def new_conversation(self, settings: Settings) -> Result:
    """Create a new conversation"""
    result = Result()

    title = "New Conversation"
    # Get registry from the command's registry property
    registry = self.registry if hasattr(self, 'registry') else None

    # Create new conversation with prompt if available
    prompt = settings.active_prompt.prompt_text if settings.active_prompt else ""

    conversation = Conversation.create_conversation(
      base_directory=settings.files_directory,
      title=title,
      prompt=prompt,
      registry=registry
    )

    if conversation:
      settings.active_conversation = conversation
      result.data = conversation
      result.message = f"Created new conversation: {title} (ID: {conversation.file_id})"
    else:
      result = Result.fail("Failed to create conversation")

    return result

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
  def print_conversation(self, settings: Settings, conversation_id: str = None) -> Result:
    """Print the current conversation or a specific conversation"""
    result = Result()

    # Get registry from the command's registry property
    registry = self.registry if hasattr(self, 'registry') else None

    if conversation_id:
      conversation = Conversation.load_conversation(
        conversation_id=conversation_id,
        base_directory=settings.files_directory,
        registry=registry
      )
      if not conversation:
        return Result.fail(f"Conversation with ID {conversation_id} not found")
    elif settings.active_conversation:
      conversation = settings.active_conversation
    else:
      return Result.fail("No active conversation selected")

    output = [f"Conversation: {conversation.title}"]

    for message in conversation.messages:
      output.append(f"-> {message.speaker.value.upper()}")
      output.append(message.content)

    result.data = conversation
    result.message = "\n".join(output)
    return result
