"""
API deployment method plugin.

This deployment method handles API-based models that make remote calls
to services like OpenAI, Anthropic, etc.
"""

import logging
from typing import Any, Dict, Iterator, Type

from .base import BaseDeployment
from ._run import deploy_and_stream
from claia.core.data import Conversation
from claia.core.data.chunks import BaseChunk
from ..plugins.base import DeploymentInfo


logger = logging.getLogger(__name__)


class APIDeploymentPlugin(BaseDeployment):
  """API deployment method plugin for remote API-based models."""

  info = DeploymentInfo(
    name="api",
    title="API Deployment",
    description="Deploy models via external API services (OpenAI, Anthropic, etc.)",
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
    return deploy_and_stream(
      model_name=model_name,
      model_class=model_class,
      conversation=conversation,
      cache=cache,
      cache_suffix="api",
      init_kwargs=init_kwargs,
      runtime_kwargs=runtime_kwargs,
    )
