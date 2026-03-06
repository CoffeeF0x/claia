"""
Local deployment method plugin.

This deployment method handles local models that run on the user's machine,
typically transformer models loaded via HuggingFace transformers.
"""

import logging
import pluggy
from typing import Dict, Any, Type, Generator

# Internal dependencies
from claia.lib.results import Result
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
class LocalDeploymentPlugin:
  """
  Local deployment method plugin for transformer-based models.

  This plugin handles deployment of models that run locally on the
  user's machine, typically using HuggingFace transformers.
  """

  @hookimpl
  def get_deployment_info(self) -> DeploymentInfo:
    """Get information about this deployment method."""
    return DeploymentInfo(
      name="local",
      title="Local Deployment",
      description="Deploy models locally using transformers/torch"
    )

  @hookimpl
  def run(self, model_name: str, model_class: Type, conversation: Conversation, cache: Dict[str, Any], **kwargs) -> Generator[str, None, Result]:
    """
    Deploy (if needed) and run inference on a local model.

    Yields tokens as they arrive from the model, manages the assistant
    message on the Conversation, and returns a Result with the full response.
    """
    try:
      cache_key = f"{model_name}:local"

      if cache_key in cache:
        model_instance = cache[cache_key]
        logger.debug(f"Using cached local model instance for {cache_key}")
      else:
        logger.debug(f"Deploying local model: {model_name}")

        device = kwargs.get('device', 'cpu')
        model_path = kwargs.get('model_path', None)
        defer_loading = kwargs.get('defer_loading', False)

        extra_kwargs = {k: v for k, v in kwargs.items() if k not in ['device', 'model_path', 'defer_loading']}

        model_instance = model_class(
          model_name=model_name,
          model_path=model_path,
          defer_loading=defer_loading,
          device=device,
          **extra_kwargs
        )

        cache[cache_key] = model_instance
        logger.debug(f"Successfully deployed and cached local model: {model_name}")

      logger.debug(f"Running local model inference: {model_name}")
      try:
        gen = model_instance.generate(conversation, **kwargs)
        message = conversation.add_message(MessageRole.ASSISTANT, "")
        full_response = ""

        for token in gen:
          full_response += token
          conversation.stream_message(message.message_id, token, append=True)
          yield token

        conversation.stream_message(message.message_id, "", append=True, end=True)

      except Exception as e:
        logger.error(f"Error during local model generate(): {e}")
        return Result.fail(f"Local model generate() failed: {e}")

      return Result.ok(full_response)

    except Exception as e:
      logger.error(f"Error running local model {model_name}: {str(e)}")
      return Result.fail(f"Failed to run local model: {str(e)}")
