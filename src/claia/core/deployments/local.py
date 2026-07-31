"""
Local deployment method plugin.

This deployment method handles local models that run on the user's machine,
typically transformer models loaded via HuggingFace transformers.
"""

import logging
from typing import Any, Dict, Iterator, Type

from .base import BaseDeployment
from claia.core.data import Conversation
from claia.core.data.adapters import conversation_to_artifacts
from claia.core.data.chunks import BaseChunk
from claia.core.data.generate import drain_generate
from ..plugins.base import DeploymentInfo


logger = logging.getLogger(__name__)


class LocalDeploymentPlugin(BaseDeployment):
  """Local deployment method plugin for transformer-based models."""

  info = DeploymentInfo(
    name="local",
    title="Local Deployment",
    description="Deploy models locally using transformers/torch",
  )

  def run(
    self,
    model_name: str,
    model_class: Type,
    conversation: Conversation,
    cache: Dict[str, Any],
    init_kwargs: Dict[str, Any],
    runtime_kwargs: Dict[str, Any],
  ) -> Iterator[BaseChunk]:
    cache_key = f"{model_name}:local"

    if cache_key in cache:
      model_instance = cache[cache_key]
      logger.debug(f"Using cached local model instance for {cache_key}")
    else:
      logger.debug(f"Deploying local model: {model_name}")
      ctor_kwargs = dict(init_kwargs)
      device = ctor_kwargs.pop("device", "cpu")
      model_path = ctor_kwargs.pop("model_path", None)
      defer_loading = ctor_kwargs.pop("defer_loading", False)

      model_instance = model_class(
        model_name=model_name,
        model_path=model_path,
        defer_loading=defer_loading,
        device=device,
        **ctor_kwargs,
      )
      cache[cache_key] = model_instance
      logger.debug(f"Successfully deployed and cached local model: {model_name}")

    artifacts = conversation_to_artifacts(conversation)
    logger.debug(f"Running local model inference: {model_name}")
    yield from drain_generate(model_instance, artifacts, runtime_kwargs)
