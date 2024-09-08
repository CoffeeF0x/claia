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
# - fix settings help display

import os

# Internal dependencies
import file, ai
from commands.registry import run as command
from errors import Result
from settings import Settings, SettingsFactory
from utilities import *



##################################################
#                   FUNCTIONS                    #
##################################################
# Get and return user input using a standardized prompt symbol
def getUserInput() -> str:
  return input(":")

# Check the user input string for any commands or queries
def processCommands(userInput: str, settings: Settings) -> Result:
  result: Result = Result()

  if userInput and userInput[0] == ":":
    result = command(userInput[1:], settings)
  else:
    runLlm(userInput, settings)

  return result

# Organize the conversation and send user query to the selected LLM
def runLlm(userInput: str, settings: Settings) -> None:
  conversation = settings.conversation
  selected_conversation = settings.selected_conversation
  selected_llm = settings.selected_llm
  conversation_directory = settings.conversation_directory
  selected_character = settings.selected_character

  apiResponse: str = ""
  messages: list[str] = []

  if len(conversation) == 0 and selected_character:
    conversation.append({"line_type": "basic", "contains": settings.characters[selected_character]})
  for each in messages:
    conversation.append({"line_type": "basic", "contains": each})

  # Append the user's prompt to the conversation if not empty, then build the message list
  if userInput:
    conversation.append({"line_type": "basic", "contains": {"role": "user", "content": userInput}})

  # Llm decision tree
  if selected_llm == "0":
    print(ai.main(settings.anthropic_api_token, "This is a message"))

  file.save_file(file.to_json(conversation), os.path.join(conversation_directory, selected_conversation))



##################################################
#                 MAIN FUNCTION                  #
##################################################
def main() -> None:
  userInput: str = ""
  result: Result = Result()

  settings = SettingsFactory.create_settings()

  while not result.is_exit():
    userInput = getUserInput()
    result = processCommands(userInput, settings)

    if result.is_error():
      print(result.get_message())

  print(result.get_message())

# Call main function
if __name__ == "__main__":
  main()
