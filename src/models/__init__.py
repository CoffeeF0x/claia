# Define the source (deployment) base object and processes

# Manage source objects (list of sources?)
# Handle source scaling if overloaded

# External dependencies
import logging
from typing import Any, Union, List, Dict, Optional

# Internal dependencies
from models.base import APIModel, LocalModel
from models.definitions import definitions
from models.sources import sources
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
  logger.debug(f"Getting model: {model_name}")

  if model_name not in definitions:
    logger.error(f"Model {model_name} not found in definitions")
    return Result.fail(f"Model {model_name} not found in definitions.")

  # Find available sources for this model
  available_sources = []
  for s in sources.keys():
    if s in definitions.get(model_name, {}).get('sources', []):
      available_sources.append(s)

  logger.debug(f"Available sources for {model_name}: {available_sources}")

  if not available_sources:
    logger.error(f"No sources available for model {model_name}")
    return Result.fail(f"No sources available for model {model_name}.")

  # Use active_model_source from settings if available, otherwise use first available source
  if settings and settings.active_model_source and settings.active_model_source in available_sources:
    chosen_source = settings.active_model_source
  else:
    chosen_source = available_sources[0]

  logger.debug(f"Selected source for {model_name}: {chosen_source}")

  # Get the model class directly from the sources dictionary
  model_class = sources[chosen_source]
  logger.debug(f"Model class for {chosen_source}: {model_class.__name__}")

  # Get model-specific configuration from the definitions
  model_config = definitions.get(model_name, {})

  # Get the model ID - if it's a list, use the first one
  model_ids = model_config.get('sources', {}).get(chosen_source, [model_name])
  if isinstance(model_ids, list):
    model_id = model_ids[0]  # Use the first model ID in the list
  else:
    model_id = model_ids

  logger.debug(f"Using model ID: {model_id}")

  if issubclass(model_class, APIModel):
    logger.debug(f"Initializing API model: {model_id} from source {chosen_source}")
    if chosen_source == "vllm":
      if not settings or not (settings.vllm_zone and settings.vllm_subdomain):
        logger.error("VLLM requires zone and subdomain to be specified in settings")
        return Result.fail("VLLM requires zone and subdomain to be specified in settings.")
      base_url = f"https://{settings.vllm_subdomain}.{settings.vllm_zone}"
      logger.debug(f"VLLM base URL: {base_url}")
      model = model_class(model_id, base_url=base_url)
    else:
      model = model_class(model_id)

    api_key = get_api_key_for_source(chosen_source, settings)
    if api_key:
      logger.debug(f"Setting API key for {chosen_source}")
      model.set_api_key(api_key)
    elif chosen_source != "vllm":  # VLLM doesn't require an API key
      logger.error(f"No API key found for source {chosen_source}")
      return Result.fail(f"No API key found for source {chosen_source}.")
  elif issubclass(model_class, LocalModel):
    logger.debug(f"Initializing local model: {model_id}")
    if model_name in settings.loaded_local_models:
      logger.debug(f"Using already loaded local model: {model_name}")
      model = settings.loaded_local_models[model_name]
    else:
      try:
        logger.debug(f"Loading new local model: {model_name}")
        if chosen_source == "transformers":
          # Get the Hugging Face API key
          api_key = get_api_key_for_source("transformers", settings)
          if api_key:
            logger.debug("Passing Hugging Face API key to model constructor")
            model = model_class(
              model_id,
              model_path=settings.model_directory if settings else "models",
              api_key=api_key
            )
          else:
            logger.warning("No Hugging Face API key found, model may have limited access")
            model = model_class(
              model_id,
              model_path=settings.model_directory if settings else "models"
            )
        else:
          model = model_class(model_id)
        if settings:
          settings.loaded_local_models[model_name] = model
          logger.debug(f"Cached local model {model_name} in settings")
      except Exception as e:
        logger.exception(f"Error loading local model {model_name}")
        return Result.fail(f"Error loading local model {model_name}: {str(e)}")
  else:
    logger.error(f"Unknown model class for source {chosen_source}")
    return Result.fail(f"Unknown model class for source {chosen_source}.")

  logger.debug(f"Successfully initialized model {model_name} from {chosen_source}")
  result.data = model
  return result

# Get the API key for the given source from settings
def get_api_key_for_source(source: str, settings: Settings) -> str:
  logger.debug(f"Getting API key for source: {source}")
  if not settings:
    logger.warning("No settings provided for API key lookup")
    return None

  api_key = None
  if source == "openai":
    api_key = settings.openai_api_token
  elif source == "anthropic":
    api_key = settings.anthropic_api_token
  elif source == "runpod":
    api_key = settings.runpod_api_token
  elif source == "openrouter":
    api_key = settings.openrouter_api_token
  elif source == "transformers":
    api_key = settings.huggingface_api_token

  if api_key:
    logger.debug(f"Found API key for {source}")
    masked_key = f"{api_key[:5]}{'*' * (len(api_key) - 5)}" if len(api_key) > 5 else "***"
    logger.debug(f"API key provided ({masked_key})")
  else:
    logger.warning(f"No API key found for {source}")

  return api_key

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
  logger.debug(f"Running model {model_name} with conversation ID: {conversation.conversation_id}")

  # Get the model instance
  result = get_model(model_name, settings)
  if result.is_error():
    logger.error(f"Failed to get model {model_name}: {result.message}")
    return result

  model = result.data
  logger.debug(f"Successfully retrieved model instance for {model_name}")

  try:
    # Get formatted messages from the conversation
    messages = conversation.get_formatted_messages()
    logger.debug(f"Got {len(messages)} formatted messages from conversation")

    # Validate messages
    if not messages or not isinstance(messages, list):
      logger.error("Invalid messages format: expected non-empty list")
      return Result.fail("Model requires a list of messages")

    # Generate response using the model
    logger.debug(f"Generating response with model {model_name}")
    response = model.generate(messages)
    logger.debug(f"Successfully generated response with model {model_name}")
    return Result(data=response)
  except Exception as e:
    logger.exception(f"Error running model {model_name}")
    return Result.fail(f"Failed to run model: {str(e)}")