"""
This module provides a ModelRegistry class for managing models in the CLAIA application.

The ModelRegistry is implemented as a singleton to ensure a single point of model
management and access throughout the application.
"""

# External dependencies
import logging
import torch
from typing import Any, List, Dict, Optional, Tuple

# Internal dependencies
from results import Result
from enums import ModelCapability

from .base import APIModel, LocalModel
from .api import OpenAIModel, AnthropicModel, RunpodModel, OpenRouterModel
from .transformers import TransformersModel, Gemma3Model, DiffusionModel
from .remote import VLLMModel
from .definitions import model_definitions
from .sources import model_sources, transformers_models
from settings import Settings
from files import Conversation



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                            MODEL REGISTRY                            #
########################################################################
class ModelRegistry:
  """
  Singleton class for managing model creation, caching, and access.

  The ModelRegistry maintains loaded models, handles model selection based on
  capabilities, and provides a unified interface for generating responses.
  """
  _instance = None

  def __new__(cls):
    """
    Create or return the singleton instance of ModelRegistry.
    """
    if cls._instance is None:
      logger.debug("Creating ModelRegistry singleton instance")
      cls._instance = super(ModelRegistry, cls).__new__(cls)
      cls._instance._initialized = False
    return cls._instance

  def __init__(self):
    if not self._initialized:
      logger.debug("Initializing Model Registry")
      # Store loaded local models with model_name as key
      self._loaded_local_models = {}
      # Cache the settings on first use
      self._settings = None
      # Cache the best available device
      self._best_device = None
      self._initialized = True

  def get_best_available_device(self) -> str:
    """
    Detect and return the best available device for model execution.
    Prefers GPU > NPU > CPU in order of availability.

    Returns:
        Device identifier string compatible with PyTorch/Transformers
    """
    # Return cached device if already determined
    if self._best_device:
      return self._best_device

    try:
      # Check for CUDA (NVIDIA GPUs)
      if torch.cuda.is_available():
        device_count = torch.cuda.device_count()
        logger.info(f"Found {device_count} CUDA GPU device(s)")
        self._best_device = "cuda"
        return self._best_device

      # Check for MPS (Apple Silicon)
      if hasattr(torch, 'mps') and torch.backends.mps.is_available():
        logger.info("Found Apple Silicon MPS")
        self._best_device = "mps"
        return self._best_device

      # Check for other specialized devices (NPUs, etc)
      # xPU (Intel)
      if hasattr(torch, 'xpu') and torch.xpu.is_available():
        logger.info("Found Intel XPU device")
        self._best_device = "xpu"
        return self._best_device

      # NOTE: NPU support depends on the specific hardware/framework
      # Different NPUs have different APIs in PyTorch

      # Some NPUs might be detected via torch.device availability
      try:
        for device_type in ["npu", "hpu", "ipu"]:  # Various NPU types
          device = torch.device(device_type)
          if device.type == device_type:
            logger.info(f"Found {device_type.upper()} device")
            self._best_device = device_type
            return self._best_device
      except:
        # Failed to detect specialized NPUs
        pass

      # Default to CPU
      logger.info("No specialized hardware detected, using CPU")
      self._best_device = "cpu"
      return self._best_device

    except ImportError:
      logger.warning("PyTorch not available, defaulting to CPU")
      self._best_device = "cpu"
      return self._best_device
    except Exception as e:
      logger.warning(f"Error detecting hardware, defaulting to CPU: {str(e)}")
      self._best_device = "cpu"
      return self._best_device

  def find_available_sources(self, model_name: str) -> List[str]:
    """Find available sources for a given model name."""
    available_sources = []
    for s in model_sources.keys():
      if s in model_definitions.get(model_name, {}).get('sources', []):
        available_sources.append(s)

    logger.debug(f"Available sources for {model_name}: {available_sources}")
    return available_sources

  def select_source(self, model_name: str, available_sources: List[str], active_model_source: Optional[str] = None) -> str:
    """
    Select the appropriate source for the model.

    Args:
        model_name: Name of the model
        available_sources: List of available sources
        active_model_source: Optional source preference

    Returns:
        The selected source name
    """
    # If source preference is provided and it's available, use it
    if active_model_source:
      if available_sources and active_model_source in available_sources:
        chosen_source = active_model_source
        logger.debug(f"Using preferred source: {chosen_source}")
      elif not available_sources:
        # If no available sources defined but preference exists, use it
        # This supports arbitrary model IDs that don't exist in definitions
        chosen_source = active_model_source
        logger.debug(f"Using preferred source (no available sources): {chosen_source}")
      else:
        # Settings source specified but not in available sources
        chosen_source = available_sources[0]
        logger.warning(f"Source {active_model_source} not available for {model_name}, using {chosen_source} instead")
    else:
      # No source preference, use first available
      if available_sources:
        chosen_source = available_sources[0]
        logger.debug(f"No source specified, using first available: {chosen_source}")
      else:
        # No available sources - this should be handled by the caller
        chosen_source = "transformers"  # Default fallback
        logger.warning(f"No available sources for {model_name}, defaulting to 'transformers'")

    return chosen_source

  def get_model_class(self, model_name: str, chosen_source: str, process_type: Optional[Any] = None) -> Tuple[Any, Result]:
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
    model_class = model_sources[chosen_source]
    logger.debug(f"Default model class for {chosen_source}: {model_class.__name__}")

    # Use specialized implementation from transformers_models if applicable
    if chosen_source == "transformers":
      # Check for specialized implementation via class_overrides
      model_config = model_definitions.get(model_name, {})
      class_overrides = model_config.get('class_overrides', {}).get(chosen_source, {})

      if class_overrides:
        # First check for a specific capability implementation if process_type provided
        impl_key = None
        if process_type:
          logger.debug(f"Checking for specific implementation for capability: {process_type}")
          if process_type in class_overrides:
            impl_key = class_overrides[process_type]
            logger.debug(f"Found implementation key for {process_type.value}: {impl_key}")

        # If no specific implementation for process_type, check for DEFAULT capability
        if not impl_key and ModelCapability.DEFAULT in class_overrides:
          impl_key = class_overrides[ModelCapability.DEFAULT]
          logger.debug(f"Using default implementation key (DEFAULT): {impl_key}")

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

  def get_model_id(self, model_name: str, chosen_source: str) -> str:
    """Get the model ID for the given model name and source."""
    model_config = model_definitions.get(model_name, {})

    # Get the model ID - if it's a list, use the first one
    model_ids = model_config.get('sources', {}).get(chosen_source, [model_name])
    if isinstance(model_ids, list):
      model_id = model_ids[0]  # Use the first model ID in the list
    else:
      model_id = model_ids

    logger.debug(f"Using model ID: {model_id}")
    return model_id

  def resolve_model_name(self, model_name: str) -> str:
    """
    Resolves a model name, potentially an alias, to its canonical key in the model_definitions dictionary.

    Args:
        model_name: Model name or alias to resolve

    Returns:
        Canonical model name (key) if found, or the original model_name if not found
    """
    # First check if the model name is a direct key in definitions
    if model_name in model_definitions:
      return model_name

    # Check if it's an alias of any defined model
    for canonical_name, model_info in model_definitions.items():
      aliases = model_info.get('aliases', [])
      if model_name in aliases:
        logger.debug(f"Resolved alias '{model_name}' to model '{canonical_name}'")
        return canonical_name

    # If not found, return the original name (for direct loading)
    return model_name

  def create_api_model(self, model_class: Any, model_id: str, chosen_source: str,
                      vllm_zone: Optional[str] = None,
                      vllm_subdomain: Optional[str] = None,
                      api_key: Optional[str] = None) -> Tuple[Any, Result]:
    """Create an API model instance."""
    result = Result()

    logger.debug(f"Initializing API model: {model_id} from source {chosen_source}")
    if chosen_source == "vllm":
      if not (vllm_zone and vllm_subdomain):
        error_msg = "VLLM requires zone and subdomain to be specified"
        logger.error(error_msg)
        return None, Result.fail(error_msg)

      base_url = f"https://{vllm_subdomain}.{vllm_zone}"
      logger.debug(f"VLLM base URL: {base_url}")
      model = model_class(model_id, base_url=base_url)
    else:
      model = model_class(model_id)

    if api_key:
      logger.debug(f"Setting API key for {chosen_source}")
      model.set_api_key(api_key)
    elif chosen_source != "vllm":  # VLLM doesn't require an API key
      error_msg = f"No API key found for source {chosen_source}"
      logger.error(error_msg)
      return None, Result.fail(error_msg)

    return model, result

  def create_local_model(self, model_name: str, model_class: Any, model_id: str, chosen_source: str,
                         device: Optional[str] = None,
                         models_directory: Optional[str] = "models",
                         api_key: Optional[str] = None) -> Tuple[Any, Result]:
    """Create a local model instance."""
    result = Result()

    logger.debug(f"Initializing local model: {model_id}")
    if model_name in self._loaded_local_models:
      logger.debug(f"Using already loaded local model: {model_name}")
      model = self._loaded_local_models[model_name]
    else:
      try:
        logger.debug(f"Loading new local model: {model_name}")
        if chosen_source == "transformers":
          model = self.create_transformers_model(model_class, model_id, device, models_directory, api_key)
        else:
          model = model_class(model_id)

        # Cache the loaded model
        self._loaded_local_models[model_name] = model
        logger.debug(f"Cached local model {model_name} in registry")
      except Exception as e:
        logger.exception(f"Error loading local model {model_name}")
        return None, Result.fail(f"Error loading local model {model_name}: {str(e)}")

    return model, result

  def create_transformers_model(self, model_class: Any, model_id: str,
                               device: Optional[str] = None,
                               model_path: Optional[str] = "models",
                               api_key: Optional[str] = None) -> Any:
    """
    Create a transformers model instance with appropriate settings.

    Args:
        model_class: Class to instantiate
        model_id: Model identifier (name or path)
        device: Device to load the model on
        model_path: Path to store/load models
        api_key: Hugging Face API key

    Returns:
        The instantiated model
    """
    # Determine the best device to use if not specified
    if not device:
      device = self.get_best_available_device()
      logger.debug(f"Automatically selected device: {device}")

    # For arbitrary model IDs, check if we need a specialized class
    capability = ModelCapability.TTT
    if model_class == TransformersModel:
      # Check model type logic can be expanded here if needed
      model_name_lower = model_id.lower()
      if 'stable-diffusion' in model_name_lower or 'sd-' in model_name_lower:
        logger.debug(f"Detected probable Stable Diffusion model, using DiffusionModel class")
        model_class = DiffusionModel
        capability = ModelCapability.TTI

    # Additional parameters for model constructor
    kwargs = {
      'model_path': model_path,
      'device': device,
      'capability': capability
    }

    if api_key:
      logger.debug("Passing Hugging Face API key to model constructor")
      kwargs['api_key'] = api_key
    else:
      logger.warning("No Hugging Face API key found, model may have limited access")

    # Create the model with appropriate arguments
    logger.debug(f"Creating {model_class.__name__} instance for model ID: {model_id}")
    model = model_class(model_id, **kwargs)

    return model

  def get_model(self, model_name: str, settings=None, process_type: Optional[Any] = None, device: Optional[str] = None) -> Result:
    """
    Get the appropriate model based on the model name, source, and optional process type.

    Args:
        model_name: The name of the model to use
        settings: Optional settings for API keys and preferences
        process_type: Optional specific capability to match (for specialized processing)
        device: Optional device to use (cuda, mps, cpu, etc). If None, uses auto-detect.

    Returns:
        Result object with the model instance as data
    """
    result = Result()
    logger.debug(f"Getting model: {model_name}")
    if process_type:
      logger.debug(f"Using process type: {process_type.value}")

    if settings:
      self._settings = settings

    # Set device preference if provided
    device_to_use = device or self.get_best_available_device()
    logger.debug(f"Using device: {device_to_use}")

    # Extract required settings
    active_model_source = self._settings.active_model_source if self._settings else None
    models_directory = self._settings.models_directory if self._settings else "models"
    vllm_zone = self._settings.vllm_zone if self._settings else None
    vllm_subdomain = self._settings.vllm_subdomain if self._settings else None

    # Resolve possible alias to canonical model name
    canonical_model_name = self.resolve_model_name(model_name)
    if canonical_model_name != model_name:
      logger.debug(f"Resolved alias '{model_name}' to canonical name '{canonical_model_name}'")
      model_name = canonical_model_name

    # Handle known models in definitions
    if model_name in model_definitions:
      logger.debug(f"Found model {model_name} in definitions")
      # Get model-specific configuration
      model_config = model_definitions.get(model_name, {})

      # Find available sources for this model
      available_sources = self.find_available_sources(model_name)

      if not available_sources:
        logger.error(f"No sources available for model {model_name}")
        return Result.fail(f"No sources available for model {model_name}.")

      # Select appropriate source
      chosen_source = self.select_source(model_name, available_sources, active_model_source)

      # Get model class with potential override based on process_type
      model_class, class_result = self.get_model_class(model_name, chosen_source, process_type)
      if class_result.is_error():
        return class_result

      # Get the model ID
      model_id = self.get_model_id(model_name, chosen_source)
    else:
      # Handle arbitrary model names not in definitions
      logger.warning(f"Model {model_name} not found in definitions, attempting direct loading")

      # Determine source based on settings or best guess
      if active_model_source:
        chosen_source = active_model_source
        logger.debug(f"Using source from settings: {chosen_source}")
      elif "/" in model_name:
        # Model names with slashes are likely HuggingFace models
        chosen_source = "transformers"
        logger.debug(f"Detected probable HuggingFace model format, using transformers source")
      else:
        # Default fallback
        chosen_source = "transformers"
        logger.debug(f"Using default source: {chosen_source}")

      # For arbitrary models, use the model name as the model ID directly
      model_id = model_name

      # Get the basic model class for the source without specialized overrides
      model_class = model_sources.get(chosen_source)
      if not model_class:
        logger.error(f"Source {chosen_source} not available")
        return Result.fail(f"Source {chosen_source} not available for model {model_name}.")

      logger.debug(f"Using model class {model_class.__name__} for {model_name}")

    # Get the appropriate API key for this source
    api_key = self.get_api_key_for_source(chosen_source)

    # Create the model instance based on its type
    if issubclass(model_class, APIModel):
      model, model_result = self.create_api_model(
        model_class,
        model_id,
        chosen_source,
        vllm_zone,
        vllm_subdomain,
        api_key
      )
      if model_result.is_error():
        return model_result
    elif issubclass(model_class, LocalModel):
      model, model_result = self.create_local_model(
        model_name,
        model_class,
        model_id,
        chosen_source,
        device_to_use,
        models_directory,
        api_key
      )
      if model_result.is_error():
        return model_result
    else:
      logger.error(f"Unknown model class for source {chosen_source}")
      return Result.fail(f"Unknown model class for source {chosen_source}.")

    logger.debug(f"Successfully initialized model {model_name} from {chosen_source}")
    result.data = model
    return result

  def get_api_key_for_source(self, source: str) -> Optional[str]:
    """
    Get the API key for the given source from cached settings.

    Args:
        source: Provider source name

    Returns:
        API key if found, None otherwise
    """
    logger.debug(f"Getting API key for source: {source}")
    if not self._settings:
      logger.warning("No settings available for API key lookup")
      return None

    api_key = None
    if source == "openai":
      api_key = self._settings.openai_api_token
    elif source == "anthropic":
      api_key = self._settings.anthropic_api_token
    elif source == "runpod":
      api_key = self._settings.runpod_api_token
    elif source == "openrouter":
      api_key = self._settings.openrouter_api_token
    elif source == "transformers":
      api_key = self._settings.huggingface_api_token

    if api_key:
      logger.debug(f"Found API key for {source}")
      masked_key = f"{api_key[:5]}{'*' * (len(api_key) - 5)}" if len(api_key) > 5 else "***"
      logger.debug(f"API key provided ({masked_key})")
    else:
      logger.warning(f"No API key found for {source}")

    return api_key

  def run(self, model_name: str, conversation,
          process_type: Optional[Any] = None,
          settings: Optional[Settings] = None,
          device: Optional[str] = None) -> Result:
    """
    Run the model with the given messages.
    This function provides a simple interface for model execution.

    Args:
        model_name: The name of the model to use
        conversation: A conversation object with the context for the model
        process_type: Optional specific capability to match (for specialized processing)
        settings: Optional settings for API keys and preferences
        device: Optional device to use (cuda, mps, cpu, etc).

    Returns:
        Result object containing the model's response
    """
    if settings:
      self._settings = settings

    logger.debug(f"Running model {model_name} with {conversation.metadata.get('message_count', 0)} messages")

    if process_type:
      logger.debug(f"Using process type: {process_type.value}")
    if device:
      logger.debug(f"Using specified device: {device}")

    # Resolve possible alias to canonical model name
    canonical_model_name = self.resolve_model_name(model_name)
    if canonical_model_name != model_name:
      logger.debug(f"Resolved alias '{model_name}' to canonical name '{canonical_model_name}'")
      model_name = canonical_model_name

    # Get the model instance
    result = self.get_model(model_name, process_type=process_type, device=device)
    if result.is_error():
      logger.error(f"Failed to get model {model_name}: {result.message}")
      return result

    model = result.data
    logger.debug(f"Successfully retrieved model instance for {model_name}")

    try:
      # Generate response using the model
      logger.debug(f"Generating response with model {model_name}")
      response = model.generate(conversation)
      logger.debug(f"Successfully generated response with model {model_name}")
      logger.debug(f"Response: {response[:50]}...")
      return Result(data=response)
    except Exception as e:
      logger.error(f"Error running model {model_name}")
      return Result.fail(f"Failed to run model: {str(e)}")

  def get_loaded_models(self) -> Dict[str, Any]:
    """Get dictionary of currently loaded local models."""
    return self._loaded_local_models

  def unload_model(self, model_name: str) -> Result:
    """Unload a model from memory."""
    if model_name in self._loaded_local_models:
      try:
        model = self._loaded_local_models[model_name]
        model.unload()
        del self._loaded_local_models[model_name]
        logger.info(f"Successfully unloaded model: {model_name}")
        return Result()
      except Exception as e:
        logger.error(f"Error unloading model {model_name}: {str(e)}")
        return Result.fail(f"Error unloading model: {str(e)}")
    else:
      return Result.fail(f"Model {model_name} is not loaded")

  def unload_all_models(self) -> Result:
    """Unload all loaded models from memory."""
    errors = []

    for model_name in list(self._loaded_local_models.keys()):
      result = self.unload_model(model_name)
      if result.is_error():
        errors.append(f"{model_name}: {result.message}")

    if errors:
      return Result.fail(f"Errors unloading models: {', '.join(errors)}")
    else:
      return Result()