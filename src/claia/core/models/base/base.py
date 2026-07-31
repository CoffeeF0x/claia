"""
Base model abstract class.

Defines the ``BaseModel`` ABC that every concrete model implementation
inherits from. Models are intentionally metadata-free: the declarative
contract for a model's generation knobs (``temperature``,
``max_tokens``, ...) lives on the architecture plugin as RUNTIME-scoped
``ParamSpec`` entries in ``ArchitectureInfo.params``. The framework
(``Registry`` + ``Manager``) filters and defaults kwargs against those
specs before calling ``generate``, so concrete models just consume the
kwargs that arrive.

Contract: artifacts in, ``ModelResponse`` out. Implementations may yield
``BaseChunk`` items while streaming and return the filled
``ModelResponse`` via the generator's return value.
"""

from abc import ABC, abstractmethod
from typing import Generator, Sequence, Union

from claia.core.data.artifacts import BaseArtifact
from claia.core.data.chunks import BaseChunk
from claia.core.data.response import ModelResponse


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
    artifacts: Sequence[BaseArtifact],
    **kwargs,
  ) -> Union[ModelResponse, Generator[BaseChunk, None, ModelResponse]]:
    """Generate a response from an ordered list of input artifacts.

    Prefer returning a ``ModelResponse`` directly. Streaming models may
    instead yield ``BaseChunk`` items and ``return`` a ``ModelResponse``
    when the generator is exhausted (StopIteration value).

    The model must NOT mutate the input artifacts; assembly into
    conversation state is the deployment / host's responsibility.

    ``kwargs`` contains the RUNTIME parameters already filtered and
    defaulted by ``Registry``/``Manager`` against the architecture's
    ``ParamSpec`` declarations.
    """
    pass
