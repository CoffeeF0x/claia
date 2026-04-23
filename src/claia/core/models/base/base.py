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
"""

from abc import ABC, abstractmethod
from typing import Generator

from claia.core.data import Conversation


########################################################################
#                              CLASSES                                 #
########################################################################
class BaseModel(ABC):
  """Abstract base class for all model implementations."""

  def __init__(self, model_name: str):
    self.model_name = model_name

  @abstractmethod
  def generate(self, conversation: Conversation, **kwargs) -> Generator[str, None, str]:
    """Generate a response based on the given conversation.

    Yields individual tokens/chunks as they become available. Returns
    the full response string when the generator is exhausted. The model
    must NOT modify the ``Conversation``; that is the deployment
    layer's responsibility.

    ``kwargs`` contains the RUNTIME parameters already filtered and
    defaulted by ``Registry``/``Manager`` against the architecture's
    ``ParamSpec`` declarations. Concrete models pull values directly —
    e.g. ``kwargs.get("temperature")`` — without redeclaring specs.
    """
    pass
