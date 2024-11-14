from commands.base import Command
from errors import Result
from settings import Settings
from models.definitions import definitions, sources
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
      elif commands[1] in ["set", "select"] and len(commands) > 3:
        setModel(commands[2], settings, commands[3])
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
    source_str = f" ({settings.active_model_source})" if settings.active_model_source else ""
    print(f"Current model: {settings.active_model}{source_str}")
  else:
    print("No model selected")

# List the available models
def listModels(settings: Settings, model_name: str = "") -> None:
  if model_name:
    # Get available sources for this model
    available_sources = [s for s in sources.keys() if model_name in sources[s]["models"]]
    
    if model_name in definitions and available_sources:
      model_info = definitions[model_name]
      print(f"Name: {model_name}")
      print(f"Title: {model_info['title']}")
      print(f"Description: {model_info['description']}")
      print(f"Available Sources: {', '.join(available_sources)}")
      
      if "training_data" in model_info:
        print(f"Training Data: {model_info['training_data']}")
      if "capabilities" in model_info:
        print(f"Capabilities: {', '.join(model_info['capabilities'])}")
    else:
      print(f"Model with name {model_name} not found or has no available sources")
  else:
    # Filter models to only those with available sources
    available_models = {
      name: model for name, model in definitions.items() 
      if any(name in sources[s]["models"] for s in sources.keys())
    }
    
    if not available_models:
      print("No models available with configured sources")
      return
      
    # Get max model name length for padding
    max_name_length = max(len(name) for name in available_models.keys())
    
    for model_name in available_models.keys():
      # Get available sources for this model
      available_sources = [s for s in sources.keys() if model_name in sources[s]["models"]]
      sources_str = f" ({', '.join(available_sources)})"
      
      # Print model name padded to align sources
      print(f"{model_name:<{max_name_length}}{sources_str}")

# Set the selected model
def setModel(model_name: str, settings: Settings, source: str = None):
  # Get available sources for this model
  available_sources = [s for s in sources.keys() if model_name in sources[s]["models"]]

  if model_name not in definitions or not available_sources:
    print(f"Model '{model_name}' not found or has no available sources")
    return
  
  if source:
    if source not in available_sources:
      print(f"Invalid source '{source}' for model '{model_name}'")
      print(f"Available sources: {', '.join(available_sources)}")
      return
    chosen_source = source
  else:
    chosen_source = available_sources[0]

  settings.active_model = model_name
  settings.active_model_source = chosen_source
  source_str = f" using source '{chosen_source}'"
  print(f"Selected model: {model_name}{source_str}")
