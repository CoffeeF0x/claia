# Internal dependencies
from commands.base import Command
from errors import Result
from file import ChatHistory
from settings import Settings



##################################################
#                 COMMAND CLASS                  #
##################################################
class ConversationCommand(Command):
  def execute(self, commands: list[str], settings: Settings) -> Result:
    result: Result = Result()

    if len(commands) > 1:
      if commands[1] == "load" and len(commands) > 2:
        loadConversation(settings, commands[2])
      elif commands[1] == "load":
        print("No conversation ID provided")
      elif commands[1] == "print" and len(commands) > 2:
        printConversation(settings, commands[2])
      elif commands[1] == "print":
        printConversation(settings)
      elif commands[1] == "new":
        newConversation(settings)
      elif commands[1] == "list":
        listConversations(settings)
      else:
        self.unrecognizedCommand()
    else:
      self.help()

    return result

  def help(self) -> None:
    print("Here are the available conversation commands:")
    print("  list")
    print("    - list any saved conversations")
    print("  new")
    print("    - start a new conversation")
    print("  print")
    print("    - display the current conversation")
    print("  load <filename>")
    print("    - load a saved conversation")



##################################################
#                   FUNCTIONS                    #
##################################################
# List all conversations
def listConversations(settings: Settings) -> None:
  conversations = ChatHistory.list_files(settings.chat_history_directory)
  for conversation in conversations:
    chat_history = ChatHistory.load(conversation, settings.chat_history_directory)
    print(f"{chat_history.unique_id}: {chat_history.title}")

# Load a stored conversation
def loadConversation(settings: Settings, conversation_id: str) -> None:
  conversations = ChatHistory.list_files(settings.chat_history_directory)
  if f"{conversation_id}.json" in conversations:
    settings.active_chat = ChatHistory.load(f"{conversation_id}.json", settings.chat_history_directory)
    print(f"Loaded conversation: {settings.active_chat.title}")
  else:
    print("Conversation not found")

# Create a new conversation
def newConversation(settings: Settings) -> None:
  title = "New Conversation"
  # title = input("Enter a title for the new conversation: ")
  new_chat = ChatHistory(settings.chat_history_directory, title, [])
  new_chat.save()
  settings.active_chat = new_chat
  print(f"Created new conversation: {title} (ID: {new_chat.unique_id})")
  print("This is now the active conversation.")

# Print the current conversation or a specific conversation
def printConversation(settings: Settings, conversation_id: str = None) -> None:
  if conversation_id:
    conversations = ChatHistory.list_files(settings.chat_history_directory)
    if f"{conversation_id}.json" in conversations:
      chat_history = ChatHistory.load(f"{conversation_id}.json", settings.chat_history_directory)
    else:
      print(f"Conversation with ID {conversation_id} not found")
      return
  elif settings.active_chat:
    chat_history = settings.active_chat
  else:
    print("No active conversation selected")
    return

  print(f"\nConversation: {chat_history.title}")
  for message in chat_history.chat_history:
    print(f"\n##### SOURCE: {message['role']}")
    print(message['content'])
