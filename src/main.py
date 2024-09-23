# TODO:
# - create new characters or update existing (need to move characters to json files)
# - add modes + add agent mode
# - add openai streaming support
# - models should be chosen by the user via key, and passed to the ai via another key pair in its definition
# - add ability to rename conversations, and perhaps have ai name conversations automatically
# - create an option to enable a server that serves and updates md files, and sync conversations to md files
# - Needs a way to filter models (since there are lots) (model list partname?)

import json

# Internal dependencies
from functions.tests import *
from functions.definitions import prompt as system_prompt
from commands.registry import run as command
from models.registry import run as model_run
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
  # If the conversation is empty and a character is selected, add the system prompt
  if len(settings.active_chat.messages()) == 0 and settings.active_prompt:
    settings.active_chat.store("system", settings.active_prompt.prompt)

  # Append the user's prompt to the conversation if not empty
  if userInput:
    settings.active_chat.store("user", userInput)

  # Run the active model
  result = model_run(settings.active_model, settings.active_chat.messages(), settings=settings)
  call_result = None

  if result.is_error():
    print(f"Error running model: {result.get_message()}")
  else:
    if result.data and "[FUNCTION_CALL]" in result.data:
      start = result.data.index("[FUNCTION_CALL]") + len("[FUNCTION_CALL]")
      end = result.data.index("[/FUNCTION_CALL]")
      function_call = json.loads(result.data[start:end])

      # Execute the function
      if function_call["name"] == "get_current_time":
        call_result = get_current_time()
      elif function_call["name"] == "get_current_date":
        call_result = get_current_date()
      elif function_call["name"] == "get_user_name":
        call_result = get_user_name()
      elif function_call["name"] == "greet_user":
        call_result = greet_user(function_call["parameters"]["name"])
      else:
        call_result = "Unknown function"

    if call_result:
      response = call_result
    else:
      response = result.data
    settings.active_chat.store("assistant", response)
    print(response)

  # Save the updated chat history
  settings.active_chat.save()



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
