"""
Abstract base class for deployments.

A deployment owns model-instance lifecycle and runs ``model.generate``
on already-translated inputs (a ``MessageSequence`` or artifact list).
Completion and errors live on ``ModelResponse``.
"""

from __future__ import annotations

import logging
from abc import ABC
from typing import Any, ClassVar, Dict, Generator, Iterator, List, Type, Union

from ..data.artifacts import BaseArtifact
from ..data.chunks import BaseChunk, RawChunk, TextChunk
from ..data.models.conversation.message_sequence import MessageSequence
from ..data.response import ModelResponse
from ..plugins.base import DeploymentInfo


logger = logging.getLogger(__name__)

ModelInputs = Union[MessageSequence, List[BaseArtifact]]


class BaseDeployment(ABC):
  """Contract and shared run path for deployments."""

  info: ClassVar[DeploymentInfo]

  def cache_key(self, model_name: str) -> str:
    """Cache key for a deployed model instance under this deployment."""
    return f"{model_name}:{self.info.name}"

  def create_model(
    self,
    model_name: str,
    model_class: Type,
    init_kwargs: Dict[str, Any],
  ) -> Any:
    """Construct a fresh model instance."""
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
    inputs: ModelInputs,
    runtime_kwargs: Dict[str, Any],
  ) -> Generator[BaseChunk, None, ModelResponse]:
    """Call ``model.generate``, yield chunks, return a ``ModelResponse``."""
    result = model.generate(inputs, **runtime_kwargs)

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
    inputs: ModelInputs,
    cache: Dict[str, Any],
    init_kwargs: Dict[str, Any],
    runtime_kwargs: Dict[str, Any],
  ) -> Iterator[BaseChunk]:
    """Deploy (if needed) and run inference on translated inputs."""
    model_instance = self.resolve_model(
      model_name, model_class, cache, init_kwargs
    )
    if isinstance(inputs, MessageSequence):
      label = f"{len(inputs)} turns ({type(inputs).__name__})"
    else:
      label = f"{len(inputs)} artifacts"
    logger.debug(f"Running model inference: {model_name} ({label})")
    yield from self.stream_generate(model_instance, inputs, runtime_kwargs)
