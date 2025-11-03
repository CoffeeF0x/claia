"""
API deployment method plugin.

This deployment method handles API-based models that make remote calls
to services like OpenAI, Anthropic, etc.
"""

import logging
from typing import Dict, Any, Type
import pluggy

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
class APIDeploymentPlugin:
  """
  API deployment method plugin for remote API-based models.

  This plugin handles deployment of models that make API calls to
  external services like OpenAI, Anthropic, Google, etc.
  """

  @hookimpl
  def get_deployment_info(self) -> DeploymentInfo:
    """Get information about this deployment method."""
    return DeploymentInfo(
      name="api",
      title="API Deployment",
      description="Deploy models via external API services (OpenAI, Anthropic, etc.)"
    )

  @hookimpl
  def run(self, model_name: str, model_class: Type, conversation: Conversation, cache: Dict[str, Any], **kwargs) -> Result:
    """
    Deploy (if needed) and run inference on an API-based model.

    Args:
        model_name: Canonical model name
        conversation: Conversation to process
        cache: Cache dictionary for model instances
        **kwargs: Additional deployment and runtime parameters

    Returns:
        Result containing the model response or error
    """
    try:
      # Create cache key for this deployment method
      cache_key = f"{model_name}:api"

      # Check cache for existing model instance
      if cache_key in cache:
        model_instance = cache[cache_key]
        logger.debug(f"Using cached API model instance for {cache_key}")
      else:
        # Deploy new model instance
        logger.debug(f"Deploying API model: {model_name}")

        # Create model instance with API key
        model_instance = model_class(
          model_name=model_name,
          **kwargs
        )

        # Cache the model instance
        cache[cache_key] = model_instance
        logger.debug(f"Successfully deployed and cached API model: {model_name}")

      # Run inference
      logger.debug(f"Running API model inference: {model_name}")
      try:
        output = model_instance.generate(conversation, **kwargs)
      except Exception as e:
        logger.error(f"Error during API model generate(): {e}")
        return Result.fail(f"API model generate() failed: {e}")

      return output if isinstance(output, Result) else Result.ok(output)

    except Exception as e:
      logger.error(f"Error running API model {model_name}: {str(e)}")
      return Result.fail(f"Failed to run API model: {str(e)}")
