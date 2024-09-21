from commands.base import Command
from errors import Result
from settings import Settings
from models.definitions import definitions
from models.registry import sources, run
import help



##################################################
#                 COMMAND CLASS                  #
##################################################
class ModelCommand(Command):
  def execute(self, commands: list[str], settings: Settings) -> Result:
    result: Result = Result()

    if len(commands) > 1:
      if commands[1] == "list" and len(commands) > 2:
        listModels(settings, commands[2])
      elif commands[1] == "list":
        listModels(settings)
      elif commands[1] in ["set", "select"] and len(commands) > 2:
        setModel(commands[2], settings)
      elif commands[1] in ["set", "select"]:
        print("No model selected")
      elif commands[1] in ["print", "current"]:
        currentModel(settings)
      else:
        help.unrecognizedCommand()
    else:
      help.modelCommands()

    return result



##################################################
#                   FUNCTIONS                    #
##################################################
# Print currently selected model
def currentModel(settings: Settings):
  if settings.active_model:
    print(f"Current model: {settings.selected_llm}")
  else:
    print("No model selected")

# List the available models
def listModels(settings: Settings, model_name: str = "") -> None:
  models = definitions.keys()
  if model_name:
    if model_name in models:
      model_info = definitions[model_name]
      print(f"Name: {model_name}")
      print(f"Title: {model_info['title']}")
      print(f"Description: {model_info['description']}")
      print(f"Sources: {', '.join(model_info['sources'])}")
      print(f"Attributes: {model_info['attributes']}")
    else:
      print(f"Model with name {model_name} not found")
  else:
    for model_name in models:
      print(model_name)

# Set the selected model
def setModel(model_name: str, settings: Settings):
  models = definitions.keys()
  if model_name in models:
    settings.active_model = model_name
    print(f"Selected model: {model_name}")
  else:
    print("Chosen model not found")
