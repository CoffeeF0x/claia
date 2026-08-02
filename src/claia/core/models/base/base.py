"""
Base model abstract class.

Contract: model inputs in (``MessageSequence`` or artifact list),
``ModelResponse`` out. Implementations may yield ``BaseChunk`` items
while streaming and return the filled ``ModelResponse`` via the
generator's return value.
"""

from abc import ABC, abstractmethod
from typing import Generator, List, Sequence, Union

from claia.core.data.artifacts import BaseArtifact
from claia.core.data.chunks import BaseChunk
from claia.core.data.models.conversation.message_sequence import MessageSequence
from claia.core.data.response import ModelResponse


ModelInputs = Union[MessageSequence, Sequence[BaseArtifact], BaseArtifact, List[BaseArtifact]]


########################################################################
#                              CLASSES                                 #
########################################################################
class BaseModel(ABC):
  """Abstract base class for all model implementations."""

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
    ``ModelResponse`` directly; streaming models may yield chunks and
    ``return`` a ``ModelResponse``.
    """
    pass
