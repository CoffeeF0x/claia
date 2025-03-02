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
from commands.registry import run as command
from models.registry import run as model_run
from errors import Result
from settings import Settings, SettingsFactory
from utilities import *
from tools import process_function_calls



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
  pruned_messages = []

  for message in settings.active_chat.messages():
    if message["role"] in ["system", "user", "assistant"]:
      pruned_messages.append(message)

  # If the conversation is empty and a character is selected, add the system prompt
  if len(pruned_messages) == 0 and settings.active_prompt:
    pruned_messages.append({"role": "system", "content": settings.active_prompt.prompt})
    settings.active_chat.store("system", settings.active_prompt.prompt)

  # Append the user's prompt to the conversation if not empty
  if userInput:
    pruned_messages.append({"role": "user", "content": userInput})
    settings.active_chat.store("user", userInput)

  # Run the active model
  result = model_run(settings.active_model, pruned_messages, settings=settings)

  if result.is_error():
    print(f"Error running model: {result.get_message()}")
  else:
    # Process any function calls in the response
    original_response = result.data
    processed_response = process_function_calls(original_response, settings)

    # Check if function calls were processed by comparing responses
    if processed_response != original_response:
      # Store the original response as a tool call if it was processed
      settings.active_chat.store("tool-call", original_response)
      response = processed_response
    else:
      response = original_response

    # Store and display the final response
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
