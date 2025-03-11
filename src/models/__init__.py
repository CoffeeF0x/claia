# Define the source (deployment) base object and processes

# Manage source objects (list of sources?)
# Handle source scaling if overloaded

# External dependencies
import logging
from typing import Any, Union, List, Dict, Optional

# Internal dependencies
from models.base import APIModel, LocalModel
from models.definitions import definitions, sources, ModelCapability
from models.processors import (
  TextToTextProcessor,
  TextToImageProcessor,
  TextToAudioProcessor,
  ImageToTextProcessor
)
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

# Get the appropriate processor for a model based on capability
def get_processor_for_model(model: Any, capability: ModelCapability) -> Result:
  """
  Factory function to get the appropriate processor for a model based on capability.

  Args:
      model: The model instance
      capability: The capability to use

  Returns:
      Result containing the appropriate processor instance
  """
  # Mapping of capabilities to processor classes
  processor_mapping = {
    ModelCapability.TTT: TextToTextProcessor,
    ModelCapability.TTI: TextToImageProcessor,
    ModelCapability.TTS: TextToAudioProcessor,
    ModelCapability.ITT: ImageToTextProcessor
  }

  try:
    processor_class = processor_mapping.get(capability)
    if not processor_class:
      return Result.fail(f"Unsupported model capability: {capability}")

    return Result(data=processor_class(model))
  except Exception as e:
    logger.error(f"Error creating processor for capability {capability}: {str(e)}")
    return Result.fail(f"Failed to create processor: {str(e)}")

# Run the model with the given conversation and settings
def run(model_name: str, conversation: Conversation, settings: Settings = None) -> Result:
  """
  Run the model with the given conversation and settings.

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

  # Determine the capability based on the model definition
  capability = ModelCapability.TTT  # Default to text-to-text
  if model_name in definitions:
    model_def = definitions[model_name]
    if "capabilities" in model_def and model_def["capabilities"]:
      capability = model_def["capabilities"][0]  # Use the first capability

  # Get the appropriate processor for the model based on capability
  processor_result = get_processor_for_model(model, capability)
  if processor_result.is_error():
    return processor_result

  processor = processor_result.data

  # Process the conversation
  return processor.process(conversation, settings)
