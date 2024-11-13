import torch

from models.base import APIModel, LocalModel
from models.definitions import definitions, sources
from settings import Settings
from errors import Result



##################################################
#                   FUNCTIONS                    #
##################################################
# Get the appropriate model based on the model name and source
def get_model(model_name: str, settings: Settings = None) -> Result:
  result = Result()

  if model_name not in definitions:
    return Result.fail(f"Model {model_name} not found in definitions.")

  # Find available sources for this model
  available_sources = [s for s in sources.keys() if model_name in sources[s]["models"]]
  if not available_sources:
    return Result.fail(f"No sources available for model {model_name}.")

  # Use active_model_source from settings if available, otherwise use first available source
  if settings and settings.active_model_source and settings.active_model_source in available_sources:
    chosen_source = settings.active_model_source
  else:
    chosen_source = available_sources[0]

  source_config = sources[chosen_source]
  model_class = source_config["class"]
  model_config = source_config["models"][model_name]

  if issubclass(model_class, APIModel):
    model = model_class(model_config["model_id"])
    api_key = get_api_key_for_source(chosen_source, settings)
    if api_key:
      model.set_api_key(api_key)
    else:
      return Result.fail(f"No API key found for source {chosen_source}.")
  elif issubclass(model_class, LocalModel):
    if model_name in settings.loaded_local_models:
      model = settings.loaded_local_models[model_name]
    else:
      print("\n\n")
      model = model_class(model_config["model_id"], settings.model_directory, 
                         device="cuda" if torch.cuda.is_available() else "cpu", 
                         log_level=settings.log_level)
      if not model.is_loaded():
        model.load()
      print("\n\n")
      settings.loaded_local_models[model_name] = model
  else:
    return Result.fail(f"Unknown model type for source {chosen_source}.")

  result.data = model
  return result

def get_api_key_for_source(source: str, settings: Settings) -> str:
  """Get the appropriate API key based on the source."""
  api_key = ""

  if source == "openai":
    api_key = settings.openai_api_token
  elif source == "anthropic":
    api_key = settings.anthropic_api_token
  elif source == "runpod":
    api_key = settings.runpod_api_token
  elif source == "openrouter":
    api_key = settings.openrouter_api_token

  return api_key

# def reset_model_context(model_name: str, settings: Settings) -> Result:
#   result = Result()

#   if model_name not in settings.loaded_local_models:
#     return Result.fail(f"Model {model_name} is not currently loaded.")

#   model = settings.loaded_local_models[model_name]

#   if hasattr(model, 'reset_context'):
#     model.reset_context()
#     result.data = f"Context reset for model {model_name}"
#   else:
#     return Result.fail(f"Model {model_name} does not support context resetting.")

#   return result

# Run the model with the given messages and settings
def run(model_name: str, messages: list, settings: Settings = None, reset_context: bool = False, **kwargs) -> Result:
  result = get_model(model_name, settings)
  if result.is_error():
    return result

  model = result.data

  # if reset_context and hasattr(model, 'reset_context'):
  #   model.reset_context()

  return Result(data=model.generate(messages, **kwargs))
