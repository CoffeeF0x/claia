"""
Dummy deployment plugin.

Provides deployment capabilities for the dummy model.
"""

import logging
from typing import Any, Dict, Iterator, Type

from .base import BaseDeployment
from claia.core.data import Conversation
from ..modality import GenerationChunk, text_chunk
from ..plugins.base import DeploymentInfo


logger = logging.getLogger(__name__)


class DummyDeploymentPlugin(BaseDeployment):
  """Deployment plugin for dummy models."""

  info = DeploymentInfo(
    name="dummy",
    title="Dummy Deployment",
    description="Dummy local deployment for testing",
  )

  def run(
    self,
    model_name: str,
    model_class: Type,
    conversation: Conversation,
    cache: Dict[str, Any],
    init_kwargs: Dict[str, Any],
    runtime_kwargs: Dict[str, Any],
  ) -> Iterator[GenerationChunk]:
    """Deploy (if needed) and run inference for dummy model. Yields ``GenerationChunk`` items."""
    del init_kwargs  # DummyModel takes no init-time configuration
    cache_key = f"{model_name}:dummy"

    if cache_key in cache:
      model_instance = cache[cache_key]
      logger.debug(f"Using cached dummy model instance for {cache_key}")
    else:
      logger.debug(f"Deploying dummy model: {model_name}")
      model_instance = model_class(model_name=model_name)
      cache[cache_key] = model_instance
      logger.debug(f"Successfully deployed and cached dummy model: {model_name}")

    logger.debug(f"Running dummy model inference: {model_name}")
    for token in model_instance.generate(conversation, **runtime_kwargs):
      yield token if isinstance(token, GenerationChunk) else text_chunk(token)
