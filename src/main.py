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
import file #, ai
from commands.registry import run as command
from errors import Result
from models.openai import OpenAITextModel
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
  if len(settings.conversation) == 0 and settings.selected_character:
    settings.conversation.append(settings.characters[settings.selected_character])
  # for each in settings.conversation:
  #   settings.conversation.append(each)

  # Append the user's prompt to the conversation if not empty, then build the message list
  if userInput:
    settings.conversation.append({"role": "user", "content": userInput})

  # print(f"Here is the conversations thus far: {settings.conversation}")
  # print(f"Here is the api key: {settings.openai_api_token}")

  # Run Llm
  # print(ai.main(settings.anthropic_api_token, "This is a message"))
  llm = OpenAITextModel("gpt-3.5-turbo")
  llm.set_api_key(settings.openai_api_token)

  # print(f"Here is the request header: {llm.session.headers}")
  settings.conversation.append(llm.generate(settings.conversation))

  print(settings.conversation)

  file.save_file(file.to_json(settings.conversation), os.path.join(settings.conversation_directory, settings.selected_conversation))



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
