"""
Local deployment method plugin.

This deployment method handles local models that run on the user's machine,
typically transformer models loaded via HuggingFace transformers.
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
  def run(self, model_name: str, model_class: Type, conversation: Conversation, cache: Dict[str, Any], **kwargs) -> Result:
    """
    Deploy (if needed) and run inference on a local model using unified interface.

    Args:
      model_name: Provider/model identifier to use with the selected architecture
      model_class: Model class to instantiate
      conversation: Conversation to process
      cache: Shared cache for model instances
      **kwargs: Additional deployment/runtime params (device, model_path, etc.)

    Returns:
      Result containing model response or error
    """
    try:
      cache_key = f"{model_name}:local"

      # Use cached instance if available
      if cache_key in cache:
        model_instance = cache[cache_key]
        logger.debug(f"Using cached local model instance for {cache_key}")
      else:
        # Deploy new local model instance
        logger.debug(f"Deploying local model: {model_name}")

        device = kwargs.get('device', 'cpu')
        model_path = kwargs.get('model_path', None)
        defer_loading = kwargs.get('defer_loading', False)

        # Pass through any extra kwargs not explicitly handled above
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

      # Run inference
      logger.debug(f"Running local model inference: {model_name}")
      try:
        output = model_instance.generate(conversation, **kwargs)
      except Exception as e:
        logger.error(f"Error during local model generate(): {e}")
        return Result.fail(f"Local model generate() failed: {e}")

      return output if isinstance(output, Result) else Result.ok(output)

    except Exception as e:
      logger.error(f"Error running local model {model_name}: {str(e)}")
      return Result.fail(f"Failed to run local model: {str(e)}")
