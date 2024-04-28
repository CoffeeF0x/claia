# TODO:
# - create new characters or update existing (need to move characters to json files)
# - add modes + add agent mode
# - print the conversation from a selected file
# - add openai streaming support
# - add ability to rename conversations, and perhaps have ai name conversations automatically
# - model (list, set)
#   > Needs a way to filter models (since there are lots) (list image or list llm?)
#   > Needs both name and type so that the system can identify how to run (json or dict?)

import os, uuid
import file, apiOpenAi, help

openAiApiToken: str = ""
localLlmApiToken: str = ""
localLlmBaseUrl: str = ""

selectedLlm: str = "2" # 1 for localLlm, 2 for OpenAi
selectedConversation: str = f"{str(uuid.uuid4())}.json"
selectedCharacter: str = "writer"

conversationDirectory: str = "history"
conversation: list[str] = []
characters = {
  "default": {"role": "system", "content": "You are a poetic assistant, skilled in explaining complex programming concepts with creative flair."},
  "writer": {"role": "system", "content": "You are a brilliant writer, always addding events and details that give life to the story, making sure to show and not tell about environments, characters, and actions."}
}

# Call the OS to clear the console
def clear() -> None:
  if os.name == "posix":
    os.system("clear")
  else:
    os.system("cls")

# Print currently selected character
def currentCharacter():
  global selectedCharacter
  if (selectedCharacter):
    print(selectedCharacter)
  else:
    print("No character selected")

# Extract all messages from the conversations object
def extractMessages(conversation) -> list[str]:
  messages: list[str] = []

  for message in conversation:
    if (message["line_type"] == "basic"):
      messages.append(message["contains"])
    elif (message["line_type"] == "openai"):
      messages.append({ "role": message["contains"]["choices"][0]["message"]["role"], "content": message["contains"]["choices"][0]["message"]["content"]})
    else:
      print("Error appending message from conversation, skipping line")

  return messages

# Return a list of all characters
def getCharacters() -> list[str]:
  global characters
  characterList: list[str] = []

  for character in characters.keys():
    str(characterList.append(character))

  return characterList

# Get and return user input using a standardized prompt symbol
def getUserInput() -> str:
  return input(":")

# List the available characters
def listCharacters(characterName: str = "") -> None:
  global characters

  if (characterName):
    print(characters[characterName]["content"])
  else:
    # print(characters) 
    for key, prompt in characters.items():
      print(key)

# List all files in the conversation directory without .json file extensions
def listConversations() -> None:
  global conversationDirectory

  for each in os.listdir(conversationDirectory):
    if (each[-5:] == ".json"):
      print(each[:-5])
    else:
      print(each)

# Load a stored conversation 
def loadConversation(conversationName: str) -> None:
  global conversation
  global conversationDirectory
  global selectedConversation

  if (conversationName[-5:] != ".json"):
    selectedConversation = conversationName + ".json"
  else:
    selectedConversation = conversationName

  if (os.path.join(conversationDirectory, selectedConversation)):
    conversation = file.load_file(os.path.join(conversationDirectory, selectedConversation))
  else:
    print("Conversation not found")

# Load environment variables to use inside the function
def loadEnv() -> bool:
  global openAiApiToken
  global localLlmApiToken
  global localLlmBaseUrl
  success: bool = True
 
  if "OPENAI_TOKEN" in os.environ:
    openAiApiToken = os.environ["OPENAI_TOKEN"]
  else:
    success = False
    print("No OpenAI API Token found")

  if "LOCALLLM_TOKEN" in os.environ:
    localLlmApiToken = os.environ["LOCALLLM_TOKEN"]
  else:
    success = False
    print("No LocalLLM API Token found")

  if "LOCALLLM_BASEURL" in os.environ:
    localLlmBaseUrl = os.environ["LOCALLLM_BASEURL"]
  else:
    success = False
    print("No LocalLLM Base URL found")

  return success

# Main function
def main() -> None:
  userInput: str = ""
  exitProgram: bool = False

  loadEnv()

  while not exitProgram:
    userInput = getUserInput()
    exitProgram = processCommands(userInput)

# Create a new conversation
def newConversation() -> None:
  global conversation
  conversation = []

# Print the current conversation
def printConversation() -> None:
  global conversation
  messages = extractMessages(conversation)
  for each in messages:
    print("\n##### SOURCE: " + each["role"])
    print(each["content"])

# Process a list of commands or return an error message
def processArgs(commands: list[str]) -> bool:
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
        loadConversation(commands[2])
      elif (commands[1] == "load"):
        print("No filename provided")
      elif (commands[1] == "print" and totalCommands > 2):
        pass # print the conversation stored in a specific file
      elif (commands[1] == "print"):
        printConversation()
      elif (commands[1] == "new"):
        newConversation()
      elif (commands[1] == "list"):
        listConversations()
      else:
        help.unrecognizedCommand()
    else:
      help.conversationCommands()

  elif (commands[0] == "character" or commands[0] == "characters"):
    if (totalCommands > 1):
      if (commands[1] == "list" and totalCommands > 2):
        listCharacters(commands[2])
      elif (commands[1] == "list"):
        listCharacters()
      elif (commands[1] == "remove" or commands[1] == "unset"):
        removeCharacter()
      elif ((commands[1] == "set" or commands[1] == "select") and totalCommands > 2):
        setCharacter(commands[2])
      elif (commands[1] == "set" or commands[1] == "select"):
        print("No character selected")
      elif (commands[1] == "print" or commands[1] == "current"):
        currentCharacter()
      else:
        help.unrecognizedCommand()
    else:
      help.characterCommands()

  else:
    help.allCommands()

  return exitProgram

# Check the user input string for any commands or queries
def processCommands(userInput: str) -> bool:
  exitProgram: bool = False

  if (userInput and userInput[0] == ":"):
    exitProgram = processArgs(userInput[1:].split(" "))
  else:
    runLlm(userInput)

  return exitProgram

# Remove character prompt
def removeCharacter():
  global selectedCharacter
  selectedCharacter = ""

# Organize the conversation and send user query to the selected LLM
def runLlm(userInput: str) -> None:
  global conversation
  global selectedConversation
  global selectedLlm
  global conversationDirectory
  global selectedCharacter

  apiResponse: str = ""
  messages: list[str] = []

  if (len(conversation) == 0 and selectedCharacter):
    conversation.append({ "line_type": "basic", "contains": characters[selectedCharacter]})
  for each in messages:
    conversation.append({ "line_type": "basic", "contains": each})

  # Append the user's prompt to the conversation if not empty, then build the message list
  if (userInput):
    conversation.append({ "line_type": "basic", "contains": {"role": "user", "content": userInput}})
  messages = extractMessages(conversation)

  # Print all messages in message list for troubleshooting
  # print("##### DEBUG #####")
  # for each in messages:
  #   print(each)
  # print("##### END OF DEBUG #####")

  # Llm decision tree
  if (selectedLlm == "1"):
    apiResponse = apiOpenAi.openaiCompletionCall(messages, localLlmApiToken, localLlmBaseUrl)
    if (isinstance(apiResponse, str)):
      conversation.append({ "line_type": "error", "contains": file.to_dict(apiResponse)})
    else:
      conversation.append({ "line_type": "openai", "contains": file.to_dict(apiResponse)})
  elif (selectedLlm == "2"):
    apiResponse = apiOpenAi.openaiCompletionCall(messages, openAiApiToken)
    if (isinstance(apiResponse, str)):
      conversation.append({ "line_type": "error", "contains": file.to_dict(apiResponse)})
    else:
      conversation.append({ "line_type": "openai", "contains": file.to_dict(apiResponse)})

  file.save_file(file.to_json(conversation), (os.path.join(conversationDirectory, selectedConversation)))

# Set the selected character
def setCharacter(character: str):
  global selectedCharacter

  if (character in getCharacters()):
    selectedCharacter = character
  else:
    print("Chosen character not found")

if __name__ == "__main__":
  main()
