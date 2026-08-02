"""
Abstract base class for deployment plugins.

A deployment takes an architecture's model class plus a conversation,
translates the conversation into a ``MessageSequence`` using the resolved
model definition's caps, and streams ``BaseChunk`` content items.
Completion and errors live on ``ModelResponse``, not as control chunks.

Shared resolve/cache/stream/translate logic lives here so concrete
deployments only override construction (``create_model``) or
``translate`` when they need provider-specific shaping.
"""

from __future__ import annotations

import logging
from abc import ABC
from typing import Any, ClassVar, Dict, Generator, Iterator, Optional, Type

from ..data import Conversation
from ..data.chunks import BaseChunk, RawChunk, TextChunk
from ..data.models.conversation.message_sequence import (
  MessageSequence,
  OrderedMessageSequence,
  SequenceMessage,
  filter_artifacts,
)
from ..data.response import ModelResponse
from ..definitions.model_definition import ModelDefinition
from ..enums.data import ArtifactType, SequenceKind
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

  def resolve_artifact(self, artifact: Any) -> Any:
    """Resolve/fetch/convert an artifact before filtering.

    Default is identity. Override for provider-specific fetch (e.g.
    ``Link`` / ``file://`` → bytes). Full conversion matrix is out of
    scope for the base path.
    """
    return artifact

  def translate(
    self,
    conversation: Conversation,
    definition: Optional[ModelDefinition] = None,
    **kwargs,
  ) -> MessageSequence:
    """Translate a conversation into a model-ready message sequence.

    1. Export the active thread from the conversation.
    2. Resolve each message artifact (hook: ``resolve_artifact``).
    3. Filter to ``definition.supported_artifacts``.
    4. Shape per ``definition.sequence_kind``.
    """
    del kwargs  # reserved for deployment-specific options
    definition = definition or ModelDefinition()
    supported = list(definition.supported_artifacts or [ArtifactType.TEXT])
    kind = definition.sequence_kind or SequenceKind.MESSAGE
    system = conversation.get_system_prompt() or None
    if system is not None and not str(system).strip():
      system = None

    turns: list[SequenceMessage] = []
    for message in conversation.export_thread():
      resolved = [self.resolve_artifact(a) for a in (message.artifacts or [])]
      filtered = filter_artifacts(resolved, supported)
      if not filtered:
        continue
      turns.append(SequenceMessage(
        role=message.speaker,
        artifacts=filtered,
        message_id=message.message_id,
      ))

    if kind == SequenceKind.ORDERED:
      return OrderedMessageSequence(messages=turns, system=system)
    if kind == SequenceKind.NONE:
      return MessageSequence.flatten(turns, system=system)
    return MessageSequence(
      messages=turns,
      system=system,
      kind=SequenceKind.MESSAGE,
    )

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
    sequence: MessageSequence,
    runtime_kwargs: Dict[str, Any],
  ) -> Generator[BaseChunk, None, ModelResponse]:
    """Call ``model.generate``, yield chunks, return a ``ModelResponse``.

    Supports both direct ``ModelResponse`` returns and streaming
    generators that yield chunks (or plain strings/bytes) and return a
    ``ModelResponse`` or scalar.
    """
    result = model.generate(sequence, **runtime_kwargs)

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
  ) -> Iterator[BaseChunk]:
    """
    Deploy (if needed), translate the conversation, and run inference.

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
    sequence = self.translate(conversation, definition)
    logger.debug(
      f"Running model inference: {model_name} "
      f"({len(sequence)} turns, kind={sequence.kind.value})"
    )
    yield from self.stream_generate(model_instance, sequence, runtime_kwargs)
