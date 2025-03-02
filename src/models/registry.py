from models.base import APIModel, LocalModel
from models.definitions import definitions, sources
from settings import Settings
from errors import Result

# Try to import optional modules
try:
  from modules import get_function_definitions
  HAS_MODULE_SYSTEM = True
except ImportError:
  # Module system not available, that's okay
  HAS_MODULE_SYSTEM = False



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
    if chosen_source == "vllm":
      if not settings or not (settings.vllm_zone and settings.vllm_subdomain):
        return Result.fail("VLLM requires zone and subdomain to be specified in settings.")
      model = model_class(model_config["model_id"], base_url=f"https://{settings.vllm_subdomain}.{settings.vllm_zone}")
    else:
      model = model_class(model_config["model_id"])

    api_key = get_api_key_for_source(chosen_source, settings)
    if api_key:
      model.set_api_key(api_key)
    elif chosen_source != "vllm":  # VLLM doesn't require an API key
      return Result.fail(f"No API key found for source {chosen_source}.")
  elif issubclass(model_class, LocalModel):
    if model_name in settings.loaded_local_models:
      model = settings.loaded_local_models[model_name]
    else:
      try:
        model = model_class(model_config["model_id"])
        if settings:
          settings.loaded_local_models[model_name] = model
      except Exception as e:
        return Result.fail(f"Error loading local model {model_name}: {str(e)}")
  else:
    return Result.fail(f"Unknown model class for source {chosen_source}.")

  result.data = model
  return result

# Get the API key for the given source from settings
def get_api_key_for_source(source: str, settings: Settings) -> str:
  if not settings:
    return None

  if source == "openai":
    return settings.openai_api_token
  elif source == "anthropic":
    return settings.anthropic_api_token
  elif source == "runpod":
    return settings.runpod_api_token
  elif source == "openrouter":
    return settings.openrouter_api_token
  else:
    return None

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

# Get function definitions from modules
def get_all_function_definitions(settings: Settings = None) -> list:
  """
  Get all function definitions, including those from modules and tools.

  Args:
    settings: Optional settings object to check if modules are enabled

  Returns:
    list: List of function definitions
  """
  # Initialize empty list for function definitions
  function_definitions = []

  # Add module function definitions if available
  if HAS_MODULE_SYSTEM:
    try:
      module_definitions = get_function_definitions()

      # Filter out disabled modules
      if settings and hasattr(settings, "disabled_modules"):
        module_definitions = [
          definition for definition in module_definitions 
          if not any(definition["name"].startswith(f"{module}_") for module in settings.disabled_modules)
        ]

      function_definitions.extend(module_definitions)
    except Exception as e:
      print(f"Error getting module function definitions: {e}")

  # TODO: Add tool function definitions when implemented
  # if HAS_TOOL_SYSTEM:
  #   try:
  #     tool_definitions = get_tool_definitions()
  #     function_definitions.extend(tool_definitions)
  #   except Exception as e:
  #     print(f"Error getting tool function definitions: {e}")

  return function_definitions

# Run the model with the given messages and settings
def run(model_name: str, messages: list, settings: Settings = None, reset_context: bool = False, **kwargs) -> Result:
  result = get_model(model_name, settings)
  if result.is_error():
    return result

  model = result.data

  # Add function definitions if supported by the model
  if hasattr(model, 'supports_functions') and model.supports_functions:
    function_definitions = get_all_function_definitions(settings)
    kwargs['functions'] = function_definitions

  # if reset_context and hasattr(model, 'reset_context'):
  #   model.reset_context()

  return Result(data=model.generate(messages, **kwargs))
