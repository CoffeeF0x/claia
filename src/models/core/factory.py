"""
Model instantiation and creation.

This module handles creating model instances from plugins and configuring them
with the appropriate settings.
"""

import logging
import torch
from typing import Any, Optional

# Internal dependencies
from common.results import Result
from common.enums.model import ModelCapability
from ..config import ModelConfig
from ..plugins import PluginManager
from ..base import BaseModel, APIModel, LocalModel


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                               CLASSES                                #
########################################################################
class ModelFactory:
  """
  Handles model instantiation and configuration.

  This component is responsible for:
  - Creating model instances from plugin classes
  - Configuring models with appropriate parameters
  - Handling different model types (API, Local, Remote)
  """

  def __init__(self, plugin_manager: PluginManager):
    """Initialize the factory with a plugin manager."""
    self.plugin_manager = plugin_manager
    self._best_device = None

  def create_model(self, model_name: str, source: str, config: ModelConfig, capability: Optional[ModelCapability] = None, device: Optional[str] = None) -> Result:
    """
    Create a model instance.

    Args:
      model_name: Name of the model to create
      source: Selected source for the model
      config: ModelConfig containing API keys and settings
      capability: Optional capability filter
      device: Optional device specification

    Returns:
      Result containing the model instance or error
    """
    try:
      # Get plugins that can handle this source
      plugins = self.plugin_manager.get_plugins_for_source(source)
      if not plugins:
        return Result.fail(f"No plugins available for source: {source}")

      logger.debug(f"Creating model {model_name} from source {source}")

      # Try each plugin until one succeeds
      for plugin in plugins:
        try:
          model_result = plugin.create_model(
            model_name=model_name,
            source=source,
            capability=capability,
            device=device,
            config=config
          )
          if model_result.success:
            return model_result
        except Exception as e:
          logger.error(f"Error creating model with plugin {plugin.__class__.__name__}: {str(e)}")

      return Result.fail(f"All plugins failed to create model {model_name} from source {source}")

    except Exception as e:
      logger.error(f"Error creating model {model_name}: {str(e)}")
      return Result.fail(f"Failed to create model: {str(e)}")

  def _create_api_model(self, model_class: type, model_id: str, chosen_source: str,
                       api_key: Optional[str] = None, **kwargs) -> Result:
    """Create an API model instance."""
    try:
      # Get the base URL for the source
      base_urls = {
        "openai": "https://api.openai.com/v1",
        "anthropic": "https://api.anthropic.com",
        "openrouter": "https://openrouter.ai/api/v1",
        "runpod": ""  # Will be set based on endpoint
      }

      base_url = base_urls.get(chosen_source, "")

      # Create the model instance
      model = model_class(model_name=model_id, base_url=base_url)

      # Set API key if provided
      if api_key:
        model.set_api_key(api_key)

      logger.debug(f"Created API model: {model_class.__name__}")
      return Result(data=model)

    except Exception as e:
      logger.error(f"Error creating API model: {str(e)}")
      return Result.fail(f"Failed to create API model: {str(e)}")

  def _create_local_model(self, model_class: type, model_name: str, model_id: str,
                         chosen_source: str, device: Optional[str] = None,
                         models_directory: Optional[str] = "models",
                         api_key: Optional[str] = None,
                         capability: Optional[ModelCapability] = None,
                         **kwargs) -> Result:
    """Create a local model instance."""
    try:
      # Determine the device to use
      if not device:
        device = self.get_best_available_device()

      # Construct model path
      model_path = f"{models_directory}/{model_id}"

      # Prepare model parameters
      model_params = {
        "model": kwargs.get("model_params", {}),
        "tokenizer": kwargs.get("tokenizer_params", {})
      }

      # Create the model instance
      if hasattr(model_class, '__init__'):
        # Check if the model class supports capability parameter (like Gemma3Model)
        import inspect
        sig = inspect.signature(model_class.__init__)

        init_kwargs = {
          "model_name": model_id,
          "model_path": model_path,
          "device": device,
          "defer_loading": kwargs.get("defer_loading", False)
        }

        # Add optional parameters if supported
        if "model_params" in sig.parameters:
          init_kwargs["model_params"] = model_params
        if "api_key" in sig.parameters:
          init_kwargs["api_key"] = api_key
        if "capability" in sig.parameters and capability:
          init_kwargs["capability"] = capability

        model = model_class(**init_kwargs)
      else:
        model = model_class(model_id, model_path, device=device, defer_loading=kwargs.get("defer_loading", False))

      logger.debug(f"Created local model: {model_class.__name__}")
      return Result(data=model)

    except Exception as e:
      logger.error(f"Error creating local model: {str(e)}")
      return Result.fail(f"Failed to create local model: {str(e)}")

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

    except Exception as e:
      logger.warning(f"Error detecting best device: {str(e)}, defaulting to CPU")
      self._best_device = "cpu"
      return self._best_device
