"""
API deployment method plugin.

This deployment method handles API-based models that make remote calls
to services like OpenAI, Anthropic, etc.
"""

import logging
from typing import Optional, Dict, List, Any, Type

# Internal dependencies
from common.results import Result
from common.files.conversation import Conversation
from ..hooks.deployment_hooks import DeploymentInfo
from ..base import BaseModel


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                               CLASSES                                #
########################################################################
class APIDeploymentPlugin:
  """
  API deployment method plugin for remote API-based models.

  This plugin handles deployment of models that make API calls to
  external services like OpenAI, Anthropic, Google, etc.
  """

  def get_deployment_info(self) -> DeploymentInfo:
    """Get information about this deployment method."""
    return DeploymentInfo(
      name="api",
      title="API Deployment",
      description="Deploy models via external API services (OpenAI, Anthropic, etc.)",
      supported_model_types=["api"],
      requires_api_key=True
    )

  def can_deploy_model(self, model_name: str, model_type: str) -> bool:
    """Check if this deployment method can handle the specified model."""
    return model_type == "api"

  def deploy_model(self, model_name: str, model_class: Type, **kwargs) -> Result:
    """
    Deploy/initialize an API-based model.

    Args:
        model_name: Canonical model name
        model_class: Model class to instantiate
        **kwargs: Additional deployment parameters (api_key, etc.)

    Returns:
        Result containing the deployed model instance or error
    """
    try:
      logger.debug(f"Deploying API model: {model_name}")

      # Extract API key from kwargs
      api_key = (
        kwargs.get('api_key') or
        kwargs.get('openai_api_key') or
        kwargs.get('anthropic_api_key') or
        kwargs.get('google_api_key')
      )

      if not api_key:
        return Result.fail(f"API key required for model {model_name}")

      # Create model instance with API key
      model_instance = model_class(
        model_name=model_name,
        api_key=api_key,
        **kwargs
      )

      logger.debug(f"Successfully deployed API model: {model_name}")
      return Result(data=model_instance)

    except Exception as e:
      logger.error(f"Error deploying API model {model_name}: {str(e)}")
      return Result.fail(f"Failed to deploy API model: {str(e)}")

  def run_model(self, model_instance: Any, conversation: Conversation, **kwargs) -> Result:
    """
    Run inference on an API-based model.

    Args:
        model_instance: The deployed model instance
        conversation: Conversation to process
        **kwargs: Additional runtime parameters

    Returns:
        Result containing the model response or error
    """
    try:
      logger.debug(f"Running API model inference")

      # API models typically have a generate or run method
      if hasattr(model_instance, 'generate'):
        result = model_instance.generate(conversation, **kwargs)
      elif hasattr(model_instance, 'run'):
        result = model_instance.run(conversation, **kwargs)
      elif hasattr(model_instance, 'chat'):
        result = model_instance.chat(conversation, **kwargs)
      else:
        return Result.fail("Model instance has no recognized inference method")

      return result

    except Exception as e:
      logger.error(f"Error running API model: {str(e)}")
      return Result.fail(f"Failed to run API model: {str(e)}")
