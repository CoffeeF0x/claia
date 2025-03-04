# Internal dependencies
from commands.base import Command, command
from errors import Result
from file import ChatHistory
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
    conversations = ChatHistory.list_files(settings.chat_history_directory)
    output = []
    for conversation in conversations:
      chat_history = ChatHistory.load(conversation, settings.chat_history_directory)
      line = f"{chat_history.unique_id}: {chat_history.title}"
      print(line)
      output.append(line)
    return "\n".join(output) if output else "No saved conversations found"

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
    conversations = ChatHistory.list_files(settings.chat_history_directory)
    if f"{conversation_id}.json" in conversations:
      settings.active_chat = ChatHistory.load(f"{conversation_id}.json", settings.chat_history_directory)
      message = f"Loaded conversation: {settings.active_chat.title}"
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
    new_chat = ChatHistory(settings.chat_history_directory, title, [])
    new_chat.save()
    settings.active_chat = new_chat
    message = f"Created new conversation: {title} (ID: {new_chat.unique_id})"
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
      conversations = ChatHistory.list_files(settings.chat_history_directory)
      if f"{conversation_id}.json" in conversations:
        chat_history = ChatHistory.load(f"{conversation_id}.json", settings.chat_history_directory)
      else:
        message = f"Conversation with ID {conversation_id} not found"
        print(message)
        return message
    elif settings.active_chat:
      chat_history = settings.active_chat
    else:
      message = "No active conversation selected"
      print(message)
      return message

    print(f"\nConversation: {chat_history.title}")
    output = [f"Conversation: {chat_history.title}"]
    for message in chat_history.chat_history:
      print(f"\n##### SOURCE: {message['role']}")
      print(message['content'])
      output.append(f"##### SOURCE: {message['role']}")
      output.append(message['content'])

    return "\n".join(output)
