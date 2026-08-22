"""
Base architecture abstract class.

An architecture owns the inference protocol for a model family:
input formatting, talking to the served model, parsing output, and
the family's feature surface. Contract: model inputs in (a
``MessageSequence`` or artifact list), ``ModelResponse`` out.
Implementations may yield ``BaseChunk`` items while streaming and
return the filled ``ModelResponse`` via the generator's return value.

Each architecture declares the deployment that serves it through the
``deployment`` class attribute (e.g. ``"api"``, ``"transformers"``);
the solver follows that link when resolving a model call.
"""

from abc import ABC, abstractmethod
from typing import ClassVar, Generator, List, Sequence, Union

from ...data.artifacts import BaseArtifact
from ...data.chunks import BaseChunk
from ...data.models.conversation.message_sequence import MessageSequence
from ...data.response import ModelResponse


ModelInputs = Union[MessageSequence, Sequence[BaseArtifact], BaseArtifact, List[BaseArtifact]]


########################################################################
#                              CLASSES                                 #
########################################################################
class BaseArchitecture(ABC):
  """Abstract base class for all architecture implementations."""

  #: Name of the deployment plugin that serves this architecture.
  deployment: ClassVar[str] = ""

  def __init__(self, model_name: str):
    self.model_name = model_name

  @abstractmethod
  def generate(
    self,
    inputs: ModelInputs,
    **kwargs,
  ) -> Union[ModelResponse, Generator[BaseChunk, None, ModelResponse]]:
    """Generate a response from model inputs.

    ``inputs`` is either a ``MessageSequence`` / ``MessageSequenceOrdered``
    or a list of artifacts (possibly empty). Prefer returning a
    ``ModelResponse`` directly; streaming implementations may yield
    chunks and ``return`` a ``ModelResponse``.

    Failure rule: raise when the request cannot start (bad inputs,
    connection refused, provider rejects the request outright); once
    content has streamed, finish with ``ModelResponse.error`` set and
    ``complete=False`` instead. Errors are never chunk content.
    """
    pass
