"""
Abstract base class for deployment plugins.

A deployment takes an architecture's model class plus a conversation,
flattens it to artifacts, and streams ``BaseChunk`` content items.
Completion and errors live on ``ModelResponse``, not as control chunks.

Shared resolve/cache/stream logic lives here so concrete deployments
only override construction (``create_model``) when they need to.
"""

from __future__ import annotations

import logging
from abc import ABC
from typing import Any, ClassVar, Dict, Generator, Iterator, Sequence, Type

from ..data import Conversation
from ..data.artifacts import BaseArtifact
from ..data.chunks import BaseChunk, RawChunk, TextChunk
from ..data.response import ModelResponse
from ..plugins.base import DeploymentInfo


logger = logging.getLogger(__name__)


class BaseDeployment(ABC):
  """Contract and shared run path for deployment plugins."""

  info: ClassVar[DeploymentInfo]

  def get_deployment_info(self) -> DeploymentInfo:
    """Return metadata describing this deployment method."""
    return type(self).info

  def cache_key(self, model_name: str) -> str:
    """Cache key for a deployed model instance under this deployment."""
    return f"{model_name}:{self.info.name}"

  def create_model(
    self,
    model_name: str,
    model_class: Type,
    init_kwargs: Dict[str, Any],
  ) -> Any:
    """Construct a fresh model instance.

    Override when the model constructor needs positional args beyond
    ``model_name`` (e.g. local device/path, remote server URL).
    """
    return model_class(model_name=model_name, **init_kwargs)

  def resolve_model(
    self,
    model_name: str,
    model_class: Type,
    cache: Dict[str, Any],
    init_kwargs: Dict[str, Any],
  ) -> Any:
    """Return a cached model instance, creating one if needed."""
    key = self.cache_key(model_name)
    if key in cache:
      logger.debug(f"Using cached model instance for {key}")
      return cache[key]

    logger.debug(f"Deploying model: {model_name} via {self.info.name}")
    instance = self.create_model(model_name, model_class, init_kwargs)
    cache[key] = instance
    logger.debug(f"Successfully deployed and cached model: {model_name}")
    return instance

  @staticmethod
  def normalize_chunk(item: Any) -> BaseChunk:
    """Coerce a yielded generate item into a ``BaseChunk``."""
    if isinstance(item, BaseChunk):
      return item
    if isinstance(item, str):
      return TextChunk(data=item)
    if isinstance(item, bytes):
      return RawChunk(data=item)
    return TextChunk(data=str(item))

  def stream_generate(
    self,
    model: Any,
    artifacts: Sequence[BaseArtifact],
    runtime_kwargs: Dict[str, Any],
  ) -> Generator[BaseChunk, None, ModelResponse]:
    """Call ``model.generate``, yield chunks, return a ``ModelResponse``.

    Supports both direct ``ModelResponse`` returns and streaming
    generators that yield chunks (or plain strings/bytes) and return a
    ``ModelResponse`` or scalar.
    """
    result = model.generate(artifacts, **runtime_kwargs)

    if isinstance(result, ModelResponse):
      for chunk in result.chunks:
        yield chunk
      return result

    if not hasattr(result, "__iter__") or isinstance(result, (str, bytes)):
      chunk = self.normalize_chunk(result)
      response = ModelResponse(chunks=[chunk], complete=True)
      yield chunk
      return response

    chunks = []
    try:
      iterator: Iterator = iter(result)
      while True:
        item = next(iterator)
        chunk = self.normalize_chunk(item)
        chunks.append(chunk)
        yield chunk
    except StopIteration as stop:
      value = stop.value
      if isinstance(value, ModelResponse):
        if not value.chunks:
          value.chunks = list(chunks)
        return value
      return ModelResponse(
        chunks=list(chunks),
        complete=True,
        metadata={"return": value} if value is not None else {},
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
    """
    Deploy (if needed) and run inference on a model.

    Yields ``BaseChunk`` content items as they arrive. Completion and
    errors are carried by the model's ``ModelResponse`` (generator
    return value), not by control chunks.

    Kwargs are split by ``ParamSpec`` scope at the framework boundary
    (``Registry._run_stream``) and handed in as two dicts:

    - ``init_kwargs`` — INIT-scoped kwargs for model construction
    - ``runtime_kwargs`` — RUNTIME-scoped kwargs for ``model.generate``

    Errors are raised as exceptions (typically ``DeploymentError``).
    """
    model_instance = self.resolve_model(
      model_name, model_class, cache, init_kwargs
    )
    artifacts = conversation.to_artifacts()
    logger.debug(
      f"Running model inference: {model_name} ({len(artifacts)} artifacts)"
    )
    yield from self.stream_generate(model_instance, artifacts, runtime_kwargs)
