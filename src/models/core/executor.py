"""
Model execution and generation coordination.

This module handles the execution of models and coordination of the generation
process across different model types.
"""

import logging
from typing import Optional, Any

# Internal dependencies
from common.results import Result
from common.files.conversation import Conversation
from common.enums.model import ModelCapability
from ..config import ModelConfig


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                               CLASSES                                #
########################################################################
class ModelExecutor:
  """
  Handles model execution and generation coordination.

  This component is responsible for:
  - Coordinating model execution across different types
  - Managing generation parameters and settings
  - Handling conversation context and response generation
  """

  def __init__(self):
    """Initialize the model executor."""
    self._settings = None
    logger.debug("ModelExecutor initialized")

  def execute_model(self, model: Any, conversation: Conversation,
                   process_type: Optional[ModelCapability] = None,
                   config: Optional[ModelConfig] = None,
                   **kwargs) -> Result:
    """
    Execute a model with the given conversation.

    Args:
        model: Model instance to execute
        conversation: Conversation to process
        config: ModelConfig containing API keys and configuration
        process_type: Optional specific capability to use
        **kwargs: Additional generation parameters

    Returns:
        Result containing the generated response
    """
    try:
      # Store config for API key retrieval
      if config:
        self._config = config

      logger.debug(f"Executing model {model.model_name} with {conversation.metadata.get('message_count', 0)} messages")

      if process_type:
        logger.debug(f"Using process type: {process_type.value}")

      # Prepare generation parameters
      generation_params = self._prepare_generation_params(conversation, **kwargs)

      # Generate response using the model
      logger.debug(f"Generating response with model {model.model_name}")
      response = model.generate(conversation, **generation_params)

      logger.debug(f"Successfully generated response with model {model.model_name}")
      logger.debug(f"Response: {str(response)[:50]}...")

      return Result(data=response)

    except Exception as e:
      logger.error(f"Error executing model {getattr(model, 'model_name', 'unknown')}: {str(e)}")
      return Result.fail(f"Failed to execute model: {str(e)}")

  def _prepare_generation_params(self, conversation: Conversation, **kwargs) -> dict:
    """
    Prepare generation parameters from conversation settings and kwargs.

    Args:
        conversation: Conversation object containing settings
        **kwargs: Additional parameters to include

    Returns:
        Dict of generation parameters
    """
    params = {}

    # Get conversation settings if available
    conversation_settings = conversation.get_settings()
    if conversation_settings:
      # Add streaming setting
      params["stream"] = conversation_settings.streaming

      # Add text generation settings if available
      text_settings = conversation_settings.text_settings
      if text_settings:
        # Map common settings
        setting_mappings = {
          "max_tokens": "max_new_tokens",
          "temperature": "temperature",
          "top_p": "top_p",
          "top_k": "top_k",
          "presence_penalty": "presence_penalty",
          "frequency_penalty": "frequency_penalty"
        }

        for setting_key, param_key in setting_mappings.items():
          if hasattr(text_settings, setting_key):
            value = getattr(text_settings, setting_key)
            if value is not None:
              params[param_key] = value

    # Override with any explicit kwargs
    params.update(kwargs)

    logger.debug(f"Prepared generation parameters: {list(params.keys())}")
    return params

  def get_api_key_for_source(self, source: str) -> Optional[str]:
    """
    Retrieve API key for the given source.
    
    Args:
      source: The source name (e.g., 'openai', 'anthropic')
      
    Returns:
      API key if available, None otherwise
    """
    if not hasattr(self, '_config') or not self._config:
      return None
      
    config = self._config
    api_key = config.get_api_token(source)
    
    if api_key:
      logger.debug(f"Retrieved API key for source: {source}")
      masked_key = f"{api_key[:5]}{'*' * (len(api_key) - 5)}" if len(api_key) > 5 else "***"
      logger.debug(f"API key provided ({masked_key})")
    else:
      logger.debug(f"No API key found for source: {source}")
      
    return api_key

  def validate_model_capability(self, model: Any, required_capability: ModelCapability) -> bool:
    """
    Validate that a model supports a required capability.

    Args:
        model: Model instance to check
        required_capability: Required capability

    Returns:
        True if model supports the capability, False otherwise
    """
    # Check if model has capability information
    if hasattr(model, 'capability'):
      return model.capability == required_capability
    elif hasattr(model, 'capabilities'):
      return required_capability in model.capabilities

    # For backwards compatibility, assume TTT capability for text models
    logger.debug(f"No capability info found for model, assuming TTT compatibility")
    return required_capability == ModelCapability.TTT
