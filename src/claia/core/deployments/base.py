"""
Abstract base class for deployments.

A deployment takes an architecture's model class plus a conversation,
translates the conversation into model inputs using the resolved
model definition's ``inputs``, and streams ``BaseChunk``
content items. Completion and errors live on ``ModelResponse``.
"""

from __future__ import annotations

import logging
from abc import ABC
from typing import Any, ClassVar, Dict, Generator, Iterator, List, Optional, Type, Union

from ..data import Conversation
from ..data.artifacts import BaseArtifact
from ..data.chunks import BaseChunk, RawChunk, TextChunk
from ..data.models.conversation.message_sequence import MessageSequence
from ..data.response import ModelResponse
from ..definitions.model_definition import ModelDefinition
from ..enums.data import ArtifactType
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

  def resolve_artifact(self, artifact: Any) -> Any:
    """Resolve/fetch/convert an artifact before filtering. Default: identity."""
    return artifact

  def translate(
    self,
    conversation: Conversation,
    definition: Optional[ModelDefinition] = None,
    system: Optional[str] = None,
    **kwargs,
  ) -> ModelInputs:
    """Translate a conversation into model inputs.

    - If the definition lists ``MessageSequenceOrdered`` / ``MessageSequence``,
      build that sequence (artifacts filtered to declared ArtifactTypes).
    - Otherwise take supported artifacts from the latest thread message
      (possibly empty).

    ``system`` is an optional generate-time inclusion. It is prepended
    onto a message sequence for this call only and is not written to
    the conversation.
    """
    del kwargs
    definition = definition or ModelDefinition()
    artifact_types = definition.artifact_types() or [ArtifactType.TEXT]
    sequence_cls = definition.sequence_class()

    if sequence_cls is not None:
      return conversation.to_message_sequence(
        supported_artifact_types=artifact_types,
        sequence_cls=sequence_cls,
        system=system,
      )

    thread = conversation.export_thread()
    if not thread:
      return []
    latest = thread[-1]
    out: List[BaseArtifact] = []
    for artifact in latest.artifacts or []:
      resolved = self.resolve_artifact(artifact)
      if ArtifactType.from_artifact(resolved) in artifact_types:
        out.append(resolved)
    return out

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
    conversation: Conversation,
    cache: Dict[str, Any],
    init_kwargs: Dict[str, Any],
    runtime_kwargs: Dict[str, Any],
    definition: Optional[ModelDefinition] = None,
    system: Optional[str] = None,
  ) -> Iterator[BaseChunk]:
    """Deploy (if needed), translate the conversation, and run inference."""
    model_instance = self.resolve_model(
      model_name, model_class, cache, init_kwargs
    )
    inputs = self.translate(conversation, definition, system=system)
    if isinstance(inputs, MessageSequence):
      label = f"{len(inputs)} turns ({type(inputs).__name__})"
    else:
      label = f"{len(inputs)} artifacts"
    logger.debug(f"Running model inference: {model_name} ({label})")
    yield from self.stream_generate(model_instance, inputs, runtime_kwargs)
