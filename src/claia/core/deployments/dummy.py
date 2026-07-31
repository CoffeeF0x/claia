"""
Dummy deployment plugin.

Provides deployment capabilities for the dummy model.
"""

import logging
from typing import Any, Dict, Iterator, Type

from .base import BaseDeployment
from ._run import deploy_and_stream
from claia.core.data import Conversation
from claia.core.data.chunks import BaseChunk
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
  ) -> Iterator[BaseChunk]:
    del init_kwargs  # DummyModel takes no init-time configuration
    return deploy_and_stream(
      model_name=model_name,
      model_class=model_class,
      conversation=conversation,
      cache=cache,
      cache_suffix="dummy",
      init_kwargs={},
      runtime_kwargs=runtime_kwargs,
    )
