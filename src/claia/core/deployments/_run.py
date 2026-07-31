"""Shared deployment run helper."""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterator, Type

from claia.core.data import Conversation
from claia.core.data.adapters import conversation_to_artifacts
from claia.core.data.chunks import BaseChunk
from claia.core.data.generate import drain_generate


logger = logging.getLogger(__name__)


def deploy_and_stream(
  *,
  model_name: str,
  model_class: Type,
  conversation: Conversation,
  cache: Dict[str, Any],
  cache_suffix: str,
  init_kwargs: Dict[str, Any],
  runtime_kwargs: Dict[str, Any],
) -> Iterator[BaseChunk]:
  """Resolve/cache a model instance, flatten conversation, stream chunks."""
  cache_key = f"{model_name}:{cache_suffix}"

  if cache_key in cache:
    model_instance = cache[cache_key]
    logger.debug(f"Using cached model instance for {cache_key}")
  else:
    logger.debug(f"Deploying model: {model_name}")
    model_instance = model_class(model_name=model_name, **init_kwargs)
    cache[cache_key] = model_instance
    logger.debug(f"Successfully deployed and cached model: {model_name}")

  artifacts = conversation_to_artifacts(conversation)
  logger.debug(f"Running model inference: {model_name} ({len(artifacts)} artifacts)")
  yield from drain_generate(model_instance, artifacts, runtime_kwargs)
