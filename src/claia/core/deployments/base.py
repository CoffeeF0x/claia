"""
Abstract base class for deployments.

A deployment serves an architecture: ``deploy`` turns an architecture
class into a servable instance (configure an API client, load weights;
later: start a llama.cpp/vllm server), and ``run`` relays the generate
stream between that instance and the hosting node — metering it
(timings, chunk counts) into the terminal ``ModelResponse`` as it
passes. Completion and errors live on ``ModelResponse``.
"""

from __future__ import annotations

import logging
import time
from abc import ABC
from typing import Any, ClassVar, Dict, Generator, List, Optional

from ..data.chunks import BaseChunk, RawChunk, TextChunk
from ..data.request import AgentRequest
from ..data.response import ModelResponse
from ..plugins.base import DeploymentInfo


logger = logging.getLogger(__name__)


class BaseDeployment(ABC):
  """Contract and shared relay/metering path for deployments."""

  info: ClassVar[DeploymentInfo]

  #: True when inference happens on a hosted third-party API — request
  #: data leaves the machine regardless of which node runs the client.
  #: The solver's ``DeploymentPreference`` filter reads this.
  api: ClassVar[bool] = False

  def deploy(self, request: AgentRequest) -> Any:
    """Construct a servable architecture instance."""
    return request.architecture_class(
      model_name=request.provider_model, **request.init_args
    )

  def teardown(self, instance: Any) -> None:
    """Release whatever ``deploy`` acquired. Default: nothing."""
    pass

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

  def run(
    self,
    instance: Any,
    request: AgentRequest,
  ) -> Generator[BaseChunk, None, ModelResponse]:
    """Run generate on a deployed instance, relaying and metering the stream.

    Yields the architecture's chunks unchanged and returns the terminal
    ``ModelResponse`` with metering merged into ``metadata['usage']``
    (never clobbering provider-reported fields).

    Failure rule: exceptions raised before any content streamed
    propagate (setup failure); exceptions after the first chunk are
    converted into an errored wrapper (``complete=False``).
    """
    started = time.monotonic()
    first_chunk_at: Optional[float] = None
    chunks: List[BaseChunk] = []

    def relay(chunk: BaseChunk) -> BaseChunk:
      nonlocal first_chunk_at
      if first_chunk_at is None:
        first_chunk_at = time.monotonic()
      chunks.append(chunk)
      return chunk

    try:
      result = instance.generate(request)

      if isinstance(result, ModelResponse):
        for chunk in result.chunks:
          yield relay(chunk)
        response = result
      elif not hasattr(result, "__iter__") or isinstance(result, (str, bytes)):
        yield relay(self.normalize_chunk(result))
        response = ModelResponse(chunks=list(chunks), complete=True)
      else:
        iterator = iter(result)
        while True:
          try:
            item = next(iterator)
          except StopIteration as stop:
            response = self._coerce_response(stop.value, chunks)
            break
          yield relay(self.normalize_chunk(item))
    except Exception as e:
      if not chunks:
        raise
      logger.exception(f"Generation failed mid-stream after {len(chunks)} chunk(s)")
      response = ModelResponse(chunks=list(chunks), complete=False, error=str(e))

    return self._meter(response, started, first_chunk_at)

  @staticmethod
  def _coerce_response(value: Any, chunks: List[BaseChunk]) -> ModelResponse:
    """Shape a generator's return value into a ``ModelResponse``."""
    if isinstance(value, ModelResponse):
      if not value.chunks:
        value.chunks = list(chunks)
      return value
    return ModelResponse(
      chunks=list(chunks),
      complete=True,
      metadata={"return": value} if value is not None else {},
    )

  @staticmethod
  def _meter(
    response: ModelResponse,
    started: float,
    first_chunk_at: Optional[float],
  ) -> ModelResponse:
    """Merge stream metering into ``response.metadata['usage']``."""
    usage = response.metadata.setdefault("usage", {})
    if isinstance(usage, dict):
      now = time.monotonic()
      usage.setdefault("chunks", len(response.chunks))
      usage.setdefault("duration", round(now - started, 4))
      if first_chunk_at is not None:
        usage.setdefault("time_to_first_chunk", round(first_chunk_at - started, 4))
    return response
