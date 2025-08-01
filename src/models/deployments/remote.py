"""
Remote deployment method plugin.

This deployment method handles remote models that run on remote servers,
cloud VMs, or other distributed systems.
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
class RemoteDeploymentPlugin:
  """
  Remote deployment method plugin for distributed models.

  This plugin handles deployment of models that run on remote
  servers, cloud VMs, or other distributed systems.
  """

  def get_deployment_info(self) -> DeploymentInfo:
    """Get information about this deployment method."""
    return DeploymentInfo(
      name="remote",
      title="Remote Deployment",
      description="Deploy models on remote servers or cloud VMs",
      supported_model_types=["api", "transformers", "custom"],
      requires_api_key=False
    )

  def can_deploy_model(self, model_name: str, model_type: str) -> bool:
    """Check if this deployment method can handle the specified model."""
    # Remote deployment can handle most model types
    return model_type in ["api", "transformers", "custom"]

  def deploy_model(self, model_name: str, model_class: Type, **kwargs) -> Result:
    """
    Deploy/initialize a remote model.

    Args:
        model_name: Canonical model name
        model_class: Model class to instantiate
        **kwargs: Additional deployment parameters (server_url, etc.)

    Returns:
        Result containing the deployed model instance or error
    """
    try:
      logger.debug(f"Deploying remote model: {model_name}")

      # Extract server configuration
      server_url = kwargs.get('server_url') or kwargs.get('remote_url')
      if not server_url:
        return Result.fail(f"Remote server URL required for model {model_name}")

      # Create model instance with remote configuration
      model_instance = model_class(
        model_name=model_name,
        server_url=server_url,
        **kwargs
      )

      # Test remote connection if possible
      if hasattr(model_instance, 'test_connection'):
        connection_result = model_instance.test_connection()
        if isinstance(connection_result, Result) and connection_result.is_error():
          return connection_result

      logger.debug(f"Successfully deployed remote model: {model_name}")
      return Result(data=model_instance)

    except Exception as e:
      logger.error(f"Error deploying remote model {model_name}: {str(e)}")
      return Result.fail(f"Failed to deploy remote model: {str(e)}")

  def run_model(self, model_instance: Any, conversation: Conversation, **kwargs) -> Result:
    """
    Run inference on a remote model.

    Args:
        model_instance: The deployed model instance
        conversation: Conversation to process
        **kwargs: Additional runtime parameters

    Returns:
        Result containing the model response or error
    """
    try:
      logger.debug(f"Running remote model inference")

      # Remote models typically have a generate or run method
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
      logger.error(f"Error running remote model: {str(e)}")
      return Result.fail(f"Failed to run remote model: {str(e)}")
