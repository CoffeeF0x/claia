"""
Abstract base class for deployments.

A deployment serves an architecture: ``deploy`` turns an architecture
class into a servable instance (configure an API client, load weights;
later: start a llama.cpp/vllm server), and ``run`` relays the generate
stream between that instance and the hosting node — yielding a
``MetricsChunk`` after the architecture finishes and owning terminal
state on the ``AgentResponse``. Completion and errors live on
``AgentResponse``.
"""

from __future__ import annotations

import logging
import time
from abc import ABC
from typing import Any, ClassVar, Generator, Optional

from ..data.chunks import BaseChunk, MetricsChunk, RawChunk, TextChunk
from ..data.request import AgentRequest
from ..data.response import AgentResponse
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
  ) -> AgentResponse:
    """Run generate on a deployed instance, relaying and metering the stream.

    Yields the architecture's chunks unchanged, then a ``MetricsChunk``.
    Setup failures (nothing streamed yet) raise; mid-stream failures
    mark ``complete=False`` / ``error`` on the returned ``AgentResponse``.
    """
    response = AgentResponse()
    return response.bind(self._relay(instance, request, response))

  def _relay(
    self,
    instance: Any,
    request: AgentRequest,
    response: AgentResponse,
  ) -> Generator[BaseChunk, None, None]:
    started = time.monotonic()
    first_chunk_at: Optional[float] = None
    chunk_count = 0

    def note(chunk: BaseChunk) -> BaseChunk:
      nonlocal first_chunk_at, chunk_count
      if first_chunk_at is None:
        first_chunk_at = time.monotonic()
      chunk_count += 1
      return chunk

    try:
      result = instance.generate(request)

      if not hasattr(result, "__iter__") or isinstance(result, (str, bytes)):
        yield note(self.normalize_chunk(result))
      else:
        for item in result:
          yield note(self.normalize_chunk(item))
    except Exception as e:
      if chunk_count == 0:
        raise
      logger.exception(f"Generation failed mid-stream after {chunk_count} chunk(s)")
      response.complete = False
      response.error = str(e)

    now = time.monotonic()
    yield MetricsChunk(
      duration=round(now - started, 4),
      time_to_first_chunk=(
        round(first_chunk_at - started, 4) if first_chunk_at is not None else None
      ),
      chunk_count=chunk_count,
    )
