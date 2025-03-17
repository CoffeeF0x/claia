# Define the source (deployment) base object and processes

# Manage source objects (list of sources?)
# Handle source scaling if overloaded

# External dependencies
import logging
from typing import Any, Union, List, Dict, Optional, Tuple

# Internal dependencies
from models.base import APIModel, LocalModel
from models.definitions import definitions, ModelCapability
from models.sources import sources, transformers_models
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
def get_best_available_device() -> str:
  """
  Detect and return the best available device for model execution.
  Prefers GPU > NPU > CPU in order of availability.

  Returns:
      Device identifier string compatible with PyTorch/Transformers
  """
  try:
    import torch

    # Check for CUDA (NVIDIA GPUs)
    if torch.cuda.is_available():
      device_count = torch.cuda.device_count()
      logger.info(f"Found {device_count} CUDA GPU device(s)")
      return "cuda"

    # Check for MPS (Apple Silicon)
    if hasattr(torch, 'mps') and torch.backends.mps.is_available():
      logger.info("Found Apple Silicon MPS")
      return "mps"

    # Check for other specialized devices (NPUs, etc)
    # xPU (Intel)
    if hasattr(torch, 'xpu') and torch.xpu.is_available():
      logger.info("Found Intel XPU device")
      return "xpu"

    # Note: NPU support depends on the specific hardware/framework
    # Different NPUs have different APIs in PyTorch

    # Some NPUs might be detected via torch.device availability
    try:
      for device_type in ["npu", "hpu", "ipu"]:  # Various NPU types
        device = torch.device(device_type)
        if device.type == device_type:
          logger.info(f"Found {device_type.upper()} device")
          return device_type
    except:
      # Failed to detect specialized NPUs
      pass

    # Default to CPU
    logger.info("No specialized hardware detected, using CPU")
    return "cpu"

  except ImportError:
    logger.warning("PyTorch not available, defaulting to CPU")
    return "cpu"
  except Exception as e:
    logger.warning(f"Error detecting hardware, defaulting to CPU: {str(e)}")
    return "cpu"


def find_available_sources(model_name: str) -> List[str]:
  """Find available sources for a given model name."""
  available_sources = []
  for s in sources.keys():
    if s in definitions.get(model_name, {}).get('sources', []):
      available_sources.append(s)

  logger.debug(f"Available sources for {model_name}: {available_sources}")
  return available_sources


def select_source(model_name: str, available_sources: List[str], settings: Optional[Settings] = None) -> str:
  """Select the appropriate source for the model."""
  if settings and settings.active_model_source and settings.active_model_source in available_sources:
    chosen_source = settings.active_model_source
  else:
    chosen_source = available_sources[0]

  logger.debug(f"Selected source for {model_name}: {chosen_source}")
  return chosen_source


def get_model_class(model_name: str, chosen_source: str, process_type: Optional[Any] = None) -> Tuple[Any, Result]:
  """
  Get the model class, checking for specialized implementations.

  Args:
      model_name: Name of the model to use
      chosen_source: Source/provider for the model
      process_type: Optional specific capability to match (for specialized processing)

  Returns:
      Tuple containing the model class and a Result object
  """
  result = Result()

  # Get the model class directly from the sources dictionary
  model_class = sources[chosen_source]
  logger.debug(f"Default model class for {chosen_source}: {model_class.__name__}")

  # Use specialized implementation from transformers_models if applicable
  if chosen_source == "transformers":
    # Check for specialized implementation via class_overrides
    model_config = definitions.get(model_name, {})
    class_overrides = model_config.get('class_overrides', {}).get(chosen_source, {})

    if class_overrides:
      # First check for a specific capability implementation if process_type provided
      impl_key = None
      if process_type:
        logger.debug(f"Checking for specific implementation for capability: {process_type}")
        if process_type in class_overrides:
          impl_key = class_overrides[process_type]
          logger.debug(f"Found implementation key for {process_type.value}: {impl_key}")

      # If no specific implementation for process_type, check for ANY capability
      if not impl_key and ModelCapability.ANY in class_overrides:
        impl_key = class_overrides[ModelCapability.ANY]
        logger.debug(f"Using default implementation key (ANY): {impl_key}")

      # If still no implementation key, get all unique implementation keys
      if not impl_key:
        impl_keys = set(class_overrides.values())
        logger.debug(f"Found implementation keys in class_overrides: {impl_keys}")

        # If we have exactly one implementation key, use it
        if len(impl_keys) == 1:
          impl_key = next(iter(impl_keys))
          logger.debug(f"Using single available implementation: {impl_key}")
        elif len(impl_keys) > 1:
          logger.warning(f"Multiple implementation keys found for {model_name}, but no specific match: {impl_keys}")

      # If we found an implementation key, use it
      if impl_key and impl_key in transformers_models:
        model_class = transformers_models[impl_key]
        logger.debug(f"Using specialized implementation: {model_class.__name__}")
      elif impl_key:
        logger.warning(f"Implementation key '{impl_key}' not found in transformers_models")
    else:
      # Fallback: Check if model name matches a prefix in transformers_models
      for family_prefix, specialized_class in transformers_models.items():
        if model_name.startswith(family_prefix):
          logger.debug(f"Found specialized implementation by prefix for {model_name}: {specialized_class.__name__}")
          model_class = specialized_class
          break

  return model_class, result


def get_model_id(model_name: str, chosen_source: str) -> str:
  """Get the model ID for the given model name and source."""
  model_config = definitions.get(model_name, {})

  # Get the model ID - if it's a list, use the first one
  model_ids = model_config.get('sources', {}).get(chosen_source, [model_name])
  if isinstance(model_ids, list):
    model_id = model_ids[0]  # Use the first model ID in the list
  else:
    model_id = model_ids

  logger.debug(f"Using model ID: {model_id}")
  return model_id


def create_api_model(model_class: Any, model_id: str, chosen_source: str, settings: Optional[Settings] = None) -> Tuple[Any, Result]:
  """Create an API model instance."""
  result = Result()

  logger.debug(f"Initializing API model: {model_id} from source {chosen_source}")
  if chosen_source == "vllm":
    if not settings or not (settings.vllm_zone and settings.vllm_subdomain):
      error_msg = "VLLM requires zone and subdomain to be specified in settings"
      logger.error(error_msg)
      return None, Result.fail(error_msg)

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
    error_msg = f"No API key found for source {chosen_source}"
    logger.error(error_msg)
    return None, Result.fail(error_msg)

  return model, result


def create_local_model(model_name: str, model_class: Any, model_id: str, chosen_source: str,
                       settings: Optional[Settings] = None) -> Tuple[Any, Result]:
  """Create a local model instance."""
  result = Result()

  logger.debug(f"Initializing local model: {model_id}")
  if settings and model_name in settings.loaded_local_models:
    logger.debug(f"Using already loaded local model: {model_name}")
    model = settings.loaded_local_models[model_name]
  else:
    try:
      logger.debug(f"Loading new local model: {model_name}")
      if chosen_source == "transformers":
        model = create_transformers_model(model_class, model_id, settings)
      else:
        model = model_class(model_id)

      if settings:
        settings.loaded_local_models[model_name] = model
        logger.debug(f"Cached local model {model_name} in settings")
    except Exception as e:
      logger.exception(f"Error loading local model {model_name}")
      return None, Result.fail(f"Error loading local model {model_name}: {str(e)}")

  return model, result


def create_transformers_model(model_class: Any, model_id: str, settings: Optional[Settings] = None) -> Any:
  """Create a transformers model instance with appropriate settings."""
  # Get the Hugging Face API key
  api_key = get_api_key_for_source("transformers", settings)
  model_path = settings.model_directory if settings else "models"

  # Determine the best device to use
  device = getattr(settings, 'device', None)
  if not device:
    device = get_best_available_device()
    logger.debug(f"Automatically selected device: {device}")

  # Additional parameters for model constructor
  kwargs = {
    'model_path': model_path,
    'device': device
  }

  if api_key:
    logger.debug("Passing Hugging Face API key to model constructor")
    kwargs['api_key'] = api_key
  else:
    logger.warning("No Hugging Face API key found, model may have limited access")

  # Create the model with appropriate arguments
  model = model_class(model_id, **kwargs)

  return model


# Get the appropriate model based on the model name and source
def get_model(model_name: str, settings: Settings = None, process_type: Optional[Any] = None, device: Optional[str] = None) -> Result:
  """
  Get the appropriate model based on the model name, source, and optional process type.

  Args:
      model_name: The name of the model to use
      settings: Optional settings for API keys and preferences
      process_type: Optional specific capability to match (for specialized processing)
      device: Optional device to use (cuda, mps, cpu, etc). If None, uses settings.device or auto-detects.

  Returns:
      Result object with the model instance as data
  """
  result = Result()
  logger.debug(f"Getting model: {model_name}")
  if process_type:
    logger.debug(f"Using process type: {process_type.value}")

  # Set device in settings if provided
  if device and settings:
    logger.debug(f"Using specified device: {device}")
    settings.device = device
  elif device:
    settings = Settings()
    settings.device = device
    logger.debug(f"Created new settings with device: {device}")

  if model_name not in definitions:
    logger.error(f"Model {model_name} not found in definitions")
    return Result.fail(f"Model {model_name} not found in definitions.")

  # Get model-specific configuration
  model_config = definitions.get(model_name, {})

  # Find available sources for this model
  available_sources = find_available_sources(model_name)

  if not available_sources:
    logger.error(f"No sources available for model {model_name}")
    return Result.fail(f"No sources available for model {model_name}.")

  # Select appropriate source
  chosen_source = select_source(model_name, available_sources, settings)

  # Get model class with potential override based on process_type
  model_class, class_result = get_model_class(model_name, chosen_source, process_type)
  if class_result.is_error():
    return class_result

  # Get the model ID
  model_id = get_model_id(model_name, chosen_source)

  # Create the model instance based on its type
  if issubclass(model_class, APIModel):
    model, model_result = create_api_model(model_class, model_id, chosen_source, settings)
    if model_result.is_error():
      return model_result
  elif issubclass(model_class, LocalModel):
    model, model_result = create_local_model(model_name, model_class, model_id, chosen_source, settings)
    if model_result.is_error():
      return model_result
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
def run(model_name: str, conversation: Conversation, settings: Settings = None,
         process_type: Optional[Any] = None, device: Optional[str] = None) -> Result:
  """
  Run the model with the given conversation and settings.
  This function provides a simple interface for model execution.

  Args:
      model_name: The name of the model to use
      conversation: The conversation to process
      settings: Optional settings object
      process_type: Optional specific capability to match (for specialized processing)
      device: Optional device to use (cuda, mps, cpu, etc). If None, uses settings.device or auto-detects.

  Returns:
      Result object containing the model's response
  """
  logger.debug(f"Running model {model_name} with conversation ID: {conversation.conversation_id}")
  if process_type:
    logger.debug(f"Using process type: {process_type.value}")
  if device:
    logger.debug(f"Using specified device: {device}")

  # Get the model instance
  result = get_model(model_name, settings, process_type, device)
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