"""
Remote deployment method plugin.

This deployment method handles remote models that run on remote servers,
cloud VMs, or other distributed systems.
"""

import logging
import pluggy
from typing import Dict, Any, Type

# Internal dependencies
from claia.lib.results import Result
from claia.lib.data import Conversation
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
      try:
        output = model_instance.generate(conversation, **kwargs)
      except Exception as e:
        logger.error(f"Error during remote model generate(): {e}")
        return Result.fail(f"Remote model generate() failed: {e}")

      return output if isinstance(output, Result) else Result.ok(output)

    except Exception as e:
      logger.error(f"Error running remote model {model_name}: {str(e)}")
      return Result.fail(f"Failed to run remote model: {str(e)}")
