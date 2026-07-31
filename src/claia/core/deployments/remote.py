"""
Remote deployment method plugin.

This deployment method handles remote models that run on remote servers,
cloud VMs, or other distributed systems.
"""

import logging
from typing import Any, Dict, Iterator, Type

from .base import BaseDeployment
from claia.core.results import DeploymentError, Result
from claia.core.data import Conversation
from claia.core.data.adapters import conversation_to_artifacts
from claia.core.data.chunks import BaseChunk
from claia.core.data.generate import drain_generate
from ..plugins.base import DeploymentInfo


logger = logging.getLogger(__name__)


class RemoteDeploymentPlugin(BaseDeployment):
  """Remote deployment method plugin for distributed models."""

  info = DeploymentInfo(
    name="remote",
    title="Remote Deployment",
    description="Deploy models on remote servers or cloud VMs",
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
    cache_key = f"{model_name}:remote"

    if cache_key in cache:
      model_instance = cache[cache_key]
      logger.debug(f"Using cached remote model instance for {cache_key}")
    else:
      server_url = (
        init_kwargs.get("server_url")
        or init_kwargs.get("remote_url")
        or init_kwargs.get("base_url")
      )
      if not server_url:
        raise DeploymentError(f"Remote server URL required for model {model_name}")

      logger.debug(f"Deploying remote model: {model_name} -> {server_url}")
      ctor_kwargs = dict(init_kwargs)
      ctor_kwargs.setdefault("server_url", server_url)
      ctor_kwargs.setdefault("base_url", server_url)

      model_instance = model_class(model_name=model_name, **ctor_kwargs)

      if hasattr(model_instance, "test_connection"):
        conn_result = model_instance.test_connection()
        if isinstance(conn_result, Result) and conn_result.is_error():
          raise DeploymentError(conn_result.get_message())

      cache[cache_key] = model_instance
      logger.debug(f"Successfully deployed and cached remote model: {model_name}")

    artifacts = conversation_to_artifacts(conversation)
    logger.debug(f"Running remote model inference: {model_name}")
    yield from drain_generate(model_instance, artifacts, runtime_kwargs)
