"""
API deployment method plugin.

This deployment method handles API-based models that make remote calls
to services like OpenAI, Anthropic, etc.
"""

import logging
from typing import Dict, Any, Type, Iterator
import pluggy

# Internal dependencies
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
  def run(self, model_name: str, model_class: Type, conversation: Conversation, cache: Dict[str, Any], **kwargs) -> Iterator[str]:
    """
    Deploy (if needed) and run inference on an API-based model.
    Yields tokens as they arrive from the model.
    """
    cache_key = f"{model_name}:api"

    if cache_key in cache:
      model_instance = cache[cache_key]
      logger.debug(f"Using cached API model instance for {cache_key}")
    else:
      logger.debug(f"Deploying API model: {model_name}")
      model_instance = model_class(
        model_name=model_name,
        **kwargs
      )
      cache[cache_key] = model_instance
      logger.debug(f"Successfully deployed and cached API model: {model_name}")

    logger.debug(f"Running API model inference: {model_name}")
    yield from model_instance.generate(conversation, **kwargs)
