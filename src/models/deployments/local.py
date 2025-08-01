"""
Local deployment method plugin.

This deployment method handles local models that run on the user's machine,
typically transformer models loaded via HuggingFace transformers.
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
class LocalDeploymentPlugin:
  """
  Local deployment method plugin for transformer-based models.

  This plugin handles deployment of models that run locally on the
  user's machine, typically using HuggingFace transformers.
  """

  def get_deployment_info(self) -> DeploymentInfo:
    """Get information about this deployment method."""
    return DeploymentInfo(
      name="local",
      title="Local Deployment",
      description="Deploy models locally using transformers/torch",
      supported_model_types=["transformers", "custom"],
      requires_api_key=False
    )

  def can_deploy_model(self, model_name: str, model_type: str) -> bool:
    """Check if this deployment method can handle the specified model."""
    return model_type in ["transformers", "custom"]

  def deploy_model(self, model_name: str, model_class: Type, **kwargs) -> Result:
    """
    Deploy/initialize a local model.

    Args:
        model_name: Canonical model name
        model_class: Model class to instantiate
        **kwargs: Additional deployment parameters (device, etc.)

    Returns:
        Result containing the deployed model instance or error
    """
    try:
      logger.debug(f"Deploying local model: {model_name}")

      # Extract device preference
      device = kwargs.get('device', 'auto')

      # Create model instance
      model_instance = model_class(
        model_name=model_name,
        device=device,
        **kwargs
      )

      # Initialize/load the model
      if hasattr(model_instance, 'load_model'):
        load_result = model_instance.load_model()
        if isinstance(load_result, Result) and load_result.is_error():
          return load_result

      logger.debug(f"Successfully deployed local model: {model_name}")
      return Result(data=model_instance)

    except Exception as e:
      logger.error(f"Error deploying local model {model_name}: {str(e)}")
      return Result.fail(f"Failed to deploy local model: {str(e)}")

  def run_model(self, model_instance: Any, conversation: Conversation, **kwargs) -> Result:
    """
    Run inference on a local model.

    Args:
        model_instance: The deployed model instance
        conversation: Conversation to process
        **kwargs: Additional runtime parameters

    Returns:
        Result containing the model response or error
    """
    try:
      logger.debug(f"Running local model inference")

      # Local models typically have a generate or run method
      if hasattr(model_instance, 'generate'):
        result = model_instance.generate(conversation, **kwargs)
      elif hasattr(model_instance, 'run'):
        result = model_instance.run(conversation, **kwargs)
      elif hasattr(model_instance, 'forward'):
        result = model_instance.forward(conversation, **kwargs)
      else:
        return Result.fail("Model instance has no recognized inference method")

      return result

    except Exception as e:
      logger.error(f"Error running local model: {str(e)}")
      return Result.fail(f"Failed to run local model: {str(e)}")
