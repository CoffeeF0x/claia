# Define the source (deployment) base object and processes

# Manage source objects (list of sources?)
# Handle source scaling if overloaded

# External dependencies
import logging
from typing import Any, Union, List, Dict, Optional

# Internal dependencies
from models.base import APIModel, LocalModel
from models.definitions import definitions, sources
from settings import Settings
from errors import Result
from conversations import Conversation



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                              FUNCTIONS                               #
########################################################################
# Get the appropriate model based on the model name and source
def get_model(model_name: str, settings: Settings = None) -> Result:
  result = Result()

  if model_name not in definitions:
    return Result.fail(f"Model {model_name} not found in definitions.")

  # Find available sources for this model
  available_sources = []
  for s in sources.keys():
    if s in definitions.get(model_name, {}).get('sources', []):
      available_sources.append(s)
  if not available_sources:
    return Result.fail(f"No sources available for model {model_name}.")

  # Use active_model_source from settings if available, otherwise use first available source
  if settings and settings.active_model_source and settings.active_model_source in available_sources:
    chosen_source = settings.active_model_source
  else:
    chosen_source = available_sources[0]

  # Get the model class directly from the sources dictionary
  model_class = sources[chosen_source]

  # Get model-specific configuration from the definitions
  model_config = definitions.get(model_name, {})

  # Get the model ID - if it's a list, use the first one
  model_ids = model_config.get('sources', {}).get(chosen_source, [model_name])
  if isinstance(model_ids, list):
    model_id = model_ids[0]  # Use the first model ID in the list

  if issubclass(model_class, APIModel):
    if chosen_source == "vllm":
      if not settings or not (settings.vllm_zone and settings.vllm_subdomain):
        return Result.fail("VLLM requires zone and subdomain to be specified in settings.")
      model = model_class(model_id, base_url=f"https://{settings.vllm_subdomain}.{settings.vllm_zone}")
    else:
      model = model_class(model_id)

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
        model = model_class(model_id)
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

# Run the model with the given conversation and settings
def run(model_name: str, conversation: Conversation, settings: Settings = None) -> Result:
  """
  Run the model with the given conversation and settings.
  This function provides a simple interface for model execution.

  Args:
      model_name: The name of the model to use
      conversation: The conversation to process
      settings: Optional settings object

  Returns:
      Result object containing the model's response
  """
  # Get the model instance
  result = get_model(model_name, settings)
  if result.is_error():
    return result

  model = result.data

  try:
    # Get formatted messages from the conversation
    messages = conversation.get_formatted_messages()

    # Validate messages
    if not messages or not isinstance(messages, list):
      return Result.fail("Model requires a list of messages")

    # Generate response using the model
    response = model.generate(messages)
    return Result(data=response)
  except Exception as e:
    logger.error(f"Error running model {model_name}: {str(e)}")
    return Result.fail(f"Failed to run model: {str(e)}")