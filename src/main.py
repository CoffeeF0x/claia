# TODO:
# - create new characters or update existing (need to move characters to json files)
# - add modes + add agent mode
# - print the conversation from a selected file
# - add openai streaming support
# - add ability to rename conversations, and perhaps have ai name conversations automatically
# - create an option to enable a server that serves and updates md files, and sync conversations to md files
# - model (list, set)
#   > Needs a way to filter models (since there are lots) (list image or list llm?)
#   > Needs both name and type so that the system can identify how to run (json or dict?)

import os
import file, help, ai
# import api.openAi
# import api.slate
# import tests.streaming, tests.record, tests.techwithtimCodeGenerator, tests.index #, tests.audio

from settings import Settings



##################################################
#               UTILITY FUNCTIONS                #
##################################################
# Clear the console
def clear() -> None:
  if os.name == "posix":
    os.system("clear")
  else:
    os.system("cls")

# Get and return user input using a standardized prompt symbol
def getUserInput() -> str:
  return input(":")



##################################################
#               CHARACTER FUNCTIONS              #
##################################################
# Print currently selected character
def currentCharacter(settings: Settings):
  if settings.selectedCharacter:
    print(settings.selectedCharacter)
  else:
    print("No character selected")

# Return a list of all characters
def getCharacters(settings: Settings) -> list[str]:
  characterList: list[str] = []

  for character in settings.characters.keys():
    characterList.append(character)

  return characterList

# List the available characters
def listCharacters(settings: Settings, characterName: str = "") -> None:
  if characterName:
    print(settings.characters[characterName]["content"])
  else:
    for key, prompt in settings.characters.items():
      print(key)

# Remove character prompt
def removeCharacter(settings: Settings) -> None:
  settings.selectedCharacter = ""

# Set the selected character
def setCharacter(character: str, settings: Settings):
  if (character in getCharacters(settings)):
    settings.selectedCharacter = character
  else:
    print("Chosen character not found")



##################################################
#             CONVERSATION FUNCTIONS             #
##################################################
# List all files in the conversation directory without .json file extensions
def listConversations(settings: Settings) -> None:
  for each in os.listdir(settings.conversationDirectory):
    if each[-5:] == ".json":
      print(each[:-5])
    else:
      print(each)

# Load a stored conversation
def loadConversation(settings: Settings, conversationName: str) -> None:
  if (conversationName[-5:] != ".json"):
    settings.selectedConversation = conversationName + ".json"
  else:
    settings.selectedConversation = conversationName

  if (os.path.join(settings.conversationDirectory, settings.selectedConversation)):
    settings.conversation = file.load_file(os.path.join(settings.conversationDirectory, settings.selectedConversation))
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



##################################################
#                 CORE FUNCTIONS                 #
##################################################
# Process a list of commands or return an error message
def processArgs(commands: list[str], settings: Settings) -> bool:
  exitProgram: bool = False
  totalCommands: int = len(commands)
  commandCounter: int = 0

  # Prune empty commands
  commandCounter = len(commands)
  while commandCounter != 0 and len(commands) > 1:
    commandCounter -= 1
    if (not commands[commandCounter]):
      commands.pop(commandCounter)

  # Update total commands
  totalCommands = len(commands)

  # Decision tree
  if (commands[0] == "s" or commands[0] == "sys" or commands[0] == "system"):
    if (totalCommands > 1):
      if (commands[1] == "q" or commands[1] == "quit" or commands[1] == "exit"):
        exitProgram = True
      elif (commands[1] == "c" or commands == "cls" or commands[1] == "clear"):
        clear()
    else:
      help.systemCommands()

  elif (commands[0] == "q" or commands[0] == "quit" or commands[0] == "exit"):
    exitProgram = True

  elif (commands[0] == "conversation" or commands[0] == "conversations"):
    if (totalCommands > 1):
      if (commands[1] == "load" and totalCommands > 2):
        loadConversation(settings, commands[2])
      elif (commands[1] == "load"):
        print("No filename provided")
      elif (commands[1] == "print" and totalCommands > 2):
        pass # print the conversation stored in a specific file
      elif (commands[1] == "print"):
        printConversation(settings)
      elif (commands[1] == "new"):
        newConversation(settings)
      elif (commands[1] == "list"):
        listConversations(settings)
      else:
        help.unrecognizedCommand()
    else:
      help.conversationCommands()

  elif (commands[0] == "character" or commands[0] == "characters"):
    if (totalCommands > 1):
      if (commands[1] == "list" and totalCommands > 2):
        listCharacters(settings, commands[2])
      elif (commands[1] == "list"):
        listCharacters(settings)
      elif (commands[1] == "remove" or commands[1] == "unset"):
        removeCharacter(settings)
      elif ((commands[1] == "set" or commands[1] == "select") and totalCommands > 2):
        setCharacter(commands[2], settings)
      elif (commands[1] == "set" or commands[1] == "select"):
        print("No character selected")
      elif (commands[1] == "print" or commands[1] == "current"):
        currentCharacter(settings)
      else:
        help.unrecognizedCommand()
    else:
      help.characterCommands()

  # elif (commands[0] == "t" or commands[0] == "test"):
  #   if (totalCommands > 1):
  #     if (commands[1] == "stream"):
  #       tests.streaming.main()
  #     elif (commands[1] == "code"):
  #       tests.techwithtimCodeGenerator.main()
  #     elif (commands[1] == "record"):
  #       tests.record.main()
  #     elif (commands[1] == "index"):
  #       tests.index.main(settings)
  #   else:
  #     pass # add help section for test commands

  else:
    help.allCommands()

  return exitProgram

# Check the user input string for any commands or queries
def processCommands(userInput: str, settings: Settings) -> bool:
  exitProgram: bool = False

  if (userInput and userInput[0] == ":"):
    exitProgram = processArgs(userInput[1:].lower().split(" "), settings)
  else:
    runLlm(userInput, settings)

  return exitProgram

# Organize the conversation and send user query to the selected LLM
def runLlm(userInput: str, settings: Settings) -> None:
  conversation = settings.conversation
  selectedConversation = settings.selectedConversation
  selectedLlm = settings.selectedLlm
  conversationDirectory = settings.conversationDirectory
  selectedCharacter = settings.selectedCharacter

  apiResponse: str = ""
  messages: list[str] = []

  if (len(conversation) == 0 and selectedCharacter):
    conversation.append({ "line_type": "basic", "contains": settings.characters[selectedCharacter]})
  for each in messages:
    conversation.append({ "line_type": "basic", "contains": each})

  # Append the user's prompt to the conversation if not empty, then build the message list
  if (userInput):
    conversation.append({ "line_type": "basic", "contains": {"role": "user", "content": userInput}})

  # Print all messages in message list for troubleshooting
  # print("##### DEBUG #####")
  # for each in messages:
  #   print(each)
  # print("##### END OF DEBUG #####")

  # Llm decision tree
  if (selectedLlm == "0"):
    print(ai.main(settings.anthropicApiToken, "This is a message"))

  # if (selectedLlm == "1"):
  #   apiResponse = api.openAi.completionCall(messages, settings.localLlmApiToken, settings.localLlmBaseUrl)
  #   if (isinstance(apiResponse, str)):
  #     conversation.append({ "line_type": "error", "contains": file.to_dict(apiResponse)})
  #   else:
  #     conversation.append({ "line_type": "openai", "contains": file.to_dict(apiResponse)})
  # elif (selectedLlm == "2"):
  #   apiResponse = api.openAi.completionCall(messages, settings.openAiApiToken)
  #   if (isinstance(apiResponse, str)):
  #     conversation.append({ "line_type": "error", "contains": file.to_dict(apiResponse)})
  #   else:
  #     conversation.append({ "line_type": "openai", "contains": file.to_dict(apiResponse)})
  # elif (selectedLlm == "3"):
  #   print(userInput)
  #   apiResponse = api.slate.send_request(userInput)
  #   print(apiResponse)

  file.save_file(file.to_json(conversation), (os.path.join(conversationDirectory, selectedConversation)))



##################################################
#                 MAIN FUNCTION                  #
##################################################
def main() -> None:
  userInput: str = ""
  exitProgram: bool = False

  settings = Settings()

  while not exitProgram:
    userInput = getUserInput()
    exitProgram = processCommands(userInput, settings)

# Call main function
if __name__ == "__main__":
  main()
