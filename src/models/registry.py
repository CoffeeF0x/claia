import torch

from models.base import APIModel, LocalModel
from models.openai import OpenAITextModel
from models.anthropic import AnthropicTextModel
from models.local import MiniCPM3LocalModel
from models.definitions import definitions
from settings import Settings
from errors import Result



##################################################
#                   FUNCTIONS                    #
##################################################
# Get the appropriate model based on the model name and source
def get_model(model_name: str, source: str = None, settings: Settings = None) -> Result:
  result = Result()

  if model_name not in definitions:
    return Result.fail(f"Model {model_name} not found in definitions.")

  model_def = definitions[model_name]
  available_sources = model_def["sources"]

  if source:
    if source not in available_sources:
      return Result.fail(f"Source {source} not available for model {model_name}.")
    chosen_source = source
  else:
    chosen_source = available_sources[0]

  if chosen_source not in sources:
    return Result.fail(f"Source {chosen_source} not implemented.")

  model_class = sources[chosen_source]

  if issubclass(model_class, APIModel):
    model = model_class(model_name)
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
      model = model_class(model_name, settings.model_directory, device = "cuda" if torch.cuda.is_available() else "cpu", log_level=settings.log_level)
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

  return api_key

# Run the model with the given messages and settings
def run(model_name: str, messages: list, source: str = None, settings: Settings = None, **kwargs) -> Result:
  result = get_model(model_name, source, settings)
  if result.is_error():
    return result

  model = result.data
  return Result(data=model.generate(messages, **kwargs))



##################################################
#            MODEL SOURCES DEFINITION            #
##################################################
sources = {
  "openai": OpenAITextModel,
  "anthropic": AnthropicTextModel,
  "local": MiniCPM3LocalModel,
}
