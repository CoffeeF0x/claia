"""
Remote deployment method plugin.

This deployment method handles remote models that run on remote servers,
cloud VMs, or other distributed systems.
"""

import logging
import pluggy
from typing import Optional, Dict, List, Any, Type

# Internal dependencies
from common.results import Result
from common.files.conversation import Conversation
from ..hooks.deployment import DeploymentInfo


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)
hookimpl = pluggy.HookimplMarker("claia_deployments")


########################################################################
#                               CLASSES                                #
########################################################################
class RemoteDeploymentPlugin:
  """
  Remote deployment method plugin for distributed models.

  This plugin handles deployment of models that run on remote
  servers, cloud VMs, or other distributed systems.
  """

  @hookimpl
  def get_deployment_info(self) -> DeploymentInfo:
    """Get information about this deployment method."""
    return DeploymentInfo(
      name="remote",
      title="Remote Deployment",
      description="Deploy models on remote servers or cloud VMs"
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

  @hookimpl
  def run(self, model_name: str, model_class: Type, conversation: Conversation, cache: Dict[str, Any], **kwargs) -> Result:
    """
    Unified run(): deploy (if needed) and run inference on a remote model.

    Handles caching and flexible URL configuration.
    """
    try:
      cache_key = f"{model_name}:remote"

      # Use cached instance if available
      if cache_key in cache:
        model_instance = cache[cache_key]
        logger.debug(f"Using cached remote model instance for {cache_key}")
      else:
        # Determine remote URL (accept multiple common keys)
        server_url = (
          kwargs.get('server_url') or
          kwargs.get('remote_url') or
          kwargs.get('base_url')
        )

        if not server_url:
          return Result.fail(f"Remote server URL required for model {model_name}")

        logger.debug(f"Deploying remote model: {model_name} -> {server_url}")

        # Pass through kwargs and provide common URL aliases
        extra_kwargs = dict(kwargs)
        extra_kwargs.setdefault('server_url', server_url)
        extra_kwargs.setdefault('base_url', server_url)

        model_instance = model_class(
          model_name=model_name,
          **extra_kwargs
        )

        # Optionally test connection if available
        if hasattr(model_instance, 'test_connection'):
          conn_result = model_instance.test_connection()
          if isinstance(conn_result, Result) and conn_result.is_error():
            return conn_result

        cache[cache_key] = model_instance
        logger.debug(f"Successfully deployed and cached remote model: {model_name}")

      # Run inference
      logger.debug(f"Running remote model inference: {model_name}")
      if hasattr(model_instance, 'generate'):
        output = model_instance.generate(conversation, **kwargs)
      elif hasattr(model_instance, 'run'):
        output = model_instance.run(conversation, **kwargs)
      elif hasattr(model_instance, 'chat'):
        output = model_instance.chat(conversation, **kwargs)
      else:
        return Result.fail("Model instance has no recognized inference method")

      return output if isinstance(output, Result) else Result.ok(output)

    except Exception as e:
      logger.error(f"Error running remote model {model_name}: {str(e)}")
      return Result.fail(f"Failed to run remote model: {str(e)}")
