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

# Try to import optional modules
try:
  from modules import discover_modules, get_module_functions, get_function_definitions
  # Initialize modules
  discover_modules()
  HAS_MODULE_SYSTEM = True
except ImportError:
  # Module system not available, that's okay
  HAS_MODULE_SYSTEM = False
  pass



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
  call_result = None

  if result.is_error():
    print(f"Error running model: {result.get_message()}")
  else:
    if result.data and "[FUNCTION_CALL]" in result.data:
      start = result.data.index("[FUNCTION_CALL]") + len("[FUNCTION_CALL]")
      end = result.data.index("[/FUNCTION_CALL]")
      function_call = json.loads(result.data[start:end])
      function_name = function_call["name"]

      # Execute the function
      # Check for module functions first
      if HAS_MODULE_SYSTEM:
        module_functions = get_module_functions(settings)
        if function_name in module_functions:
          try:
            # Call the module function with parameters
            if "parameters" in function_call:
              call_result = module_functions[function_name](**function_call["parameters"])
            else:
              call_result = module_functions[function_name]()
          except Exception as e:
            call_result = f"Error executing function {function_name}: {str(e)}"
        else:
          call_result = f"Unknown function: {function_name}"
      else:
        call_result = f"Unknown function: {function_name}"

    if call_result:
      response = call_result
      settings.active_chat.store("tool-call", result.data)
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
