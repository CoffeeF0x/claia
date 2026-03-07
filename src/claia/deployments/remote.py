"""
Remote deployment method plugin.

This deployment method handles remote models that run on remote servers,
cloud VMs, or other distributed systems.
"""

import logging
import pluggy
from typing import Dict, Any, Type, Iterator

# Internal dependencies
from claia.lib.results import DeploymentError, Result
from claia.lib.data import Conversation
from claia.lib.enums.conversation import MessageRole
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
  def run(self, model_name: str, model_class: Type, conversation: Conversation, cache: Dict[str, Any], **kwargs) -> Iterator[str]:
    """
    Deploy (if needed) and run inference on a remote model.

    Yields tokens as they arrive from the model and manages the assistant
    message on the Conversation.
    """
    cache_key = f"{model_name}:remote"

    if cache_key in cache:
      model_instance = cache[cache_key]
      logger.debug(f"Using cached remote model instance for {cache_key}")
    else:
      server_url = (
        kwargs.get('server_url') or
        kwargs.get('remote_url') or
        kwargs.get('base_url')
      )

      if not server_url:
        raise DeploymentError(f"Remote server URL required for model {model_name}")

      logger.debug(f"Deploying remote model: {model_name} -> {server_url}")

      extra_kwargs = dict(kwargs)
      extra_kwargs.setdefault('server_url', server_url)
      extra_kwargs.setdefault('base_url', server_url)

      model_instance = model_class(
        model_name=model_name,
        **extra_kwargs
      )

      if hasattr(model_instance, 'test_connection'):
        conn_result = model_instance.test_connection()
        if isinstance(conn_result, Result) and conn_result.is_error():
          raise DeploymentError(conn_result.get_message())

      cache[cache_key] = model_instance
      logger.debug(f"Successfully deployed and cached remote model: {model_name}")

    logger.debug(f"Running remote model inference: {model_name}")
    gen = model_instance.generate(conversation, **kwargs)
    message = conversation.add_message(MessageRole.ASSISTANT, "")

    for token in gen:
      conversation.stream_message(message.message_id, token, append=True)
      yield token

    conversation.stream_message(message.message_id, "", append=True, end=True)
