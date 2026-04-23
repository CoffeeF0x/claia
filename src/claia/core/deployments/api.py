"""
API deployment method plugin.

This deployment method handles API-based models that make remote calls
to services like OpenAI, Anthropic, etc.
"""

import logging
from typing import Any, Dict, Iterator, Type

from .base import BaseDeployment
from claia.core.data import Conversation
from ..modality import GenerationChunk, text_chunk
from ..plugins.base import DeploymentInfo


logger = logging.getLogger(__name__)


class APIDeploymentPlugin(BaseDeployment):
  """
  API deployment method plugin for remote API-based models.

  This plugin handles deployment of models that make API calls to
  external services like OpenAI, Anthropic, Google, etc.
  """

  info = DeploymentInfo(
    name="api",
    title="API Deployment",
    description="Deploy models via external API services (OpenAI, Anthropic, etc.)",
  )

  def run(self, model_name: str, model_class: Type, conversation: Conversation, cache: Dict[str, Any], **kwargs) -> Iterator[GenerationChunk]:
    """
    Deploy (if needed) and run inference on an API-based model.

    Yields ``GenerationChunk`` items. The underlying API models still
    yield plain string tokens from ``generate``; this deployment wraps
    each token into a ``ChunkKind.TEXT`` chunk so the framework-level
    contract is uniform across text and multi-modal providers.
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
    for token in model_instance.generate(conversation, **kwargs):
      yield token if isinstance(token, GenerationChunk) else text_chunk(token)
