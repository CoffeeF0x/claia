from os import listdir, path

# Internal dependencies
import file

from commands.base import Command
from errors import Result
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
        print("No filename provided")
      elif commands[1] == "print" and len(commands) > 2:
        pass  # print the conversation stored in a specific file
      elif commands[1] == "print":
        printConversation(settings)
      elif commands[1] == "new":
        newConversation(settings)
      elif commands[1] == "list":
        listConversations(settings)
      else:
        help.unrecognizedCommand()
    else:
      help.conversationCommands()

    return result



##################################################
#                   FUNCTIONS                    #
##################################################
# List all files in the conversation directory without .json file extensions
def listConversations(settings: Settings) -> None:
  for each in listdir(settings.conversation_directory):
    if each.endswith(".json"):
      print(each[:-5])
    else:
      print(each)

# Load a stored conversation
def loadConversation(settings: Settings, conversationName: str) -> None:
  if not conversationName.endswith(".json"):
    settings.selected_conversation = conversationName + ".json"
  else:
    settings.selected_conversation = conversationName

  full_path = path.join(settings.conversation_directory, settings.selected_conversation)
  if path.exists(full_path):
    settings.conversation = file.load_file(full_path)
  else:
    print("Conversation not found")

# Create a new conversation
def newConversation(settings: Settings) -> None:
  settings.conversation = []

# Print the current conversation
def printConversation(settings: Settings) -> None:
  for each in settings.conversation:
    print("\n##### SOURCE: " + each["role"])
    print(each["content"])
