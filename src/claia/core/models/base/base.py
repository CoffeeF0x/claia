"""
Base model abstract class.

Defines the ``BaseModel`` abstract base class that every concrete model
implementation inherits from. Concrete models declare the generation
parameters they understand via ``runtime_params`` (a list of
``ParamSpec`` with ``scope=ParamScope.RUNTIME``); ``update_settings``
consumes those specs to build the settings dict used by the model's
``generate`` method.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, List

from claia.core.data import Conversation
from claia.core.plugins.base import ParamScope, ParamSpec, SettingCategory


########################################################################
#                         COMMON RUNTIME PARAMS                        #
########################################################################
# Sensible defaults that apply to most chat-style text models. Concrete
# model classes extend or override this list by defining their own
# ``runtime_params`` class attribute.
COMMON_TEXT_RUNTIME_PARAMS: List[ParamSpec] = [
  ParamSpec(name="max_tokens", type=int, scope=ParamScope.RUNTIME, default=1000,
            category=SettingCategory.GENERATION,
            description="Maximum number of tokens to generate."),
  ParamSpec(name="temperature", type=float, scope=ParamScope.RUNTIME, default=0.7,
            category=SettingCategory.GENERATION,
            description="Sampling temperature; higher values produce more varied output."),
  ParamSpec(name="top_p", type=float, scope=ParamScope.RUNTIME, default=1.0,
            category=SettingCategory.GENERATION,
            description="Nucleus sampling probability mass."),
  ParamSpec(name="top_k", type=int, scope=ParamScope.RUNTIME, default=None,
            category=SettingCategory.GENERATION,
            description="Restrict sampling to the top-k tokens."),
  ParamSpec(name="n", type=int, scope=ParamScope.RUNTIME, default=1,
            category=SettingCategory.GENERATION,
            description="Number of completions to request per call."),
  ParamSpec(name="stop", type=list, scope=ParamScope.RUNTIME, default=None,
            category=SettingCategory.GENERATION,
            description="Sequence(s) at which generation should stop."),
  ParamSpec(name="stream", type=bool, scope=ParamScope.RUNTIME, default=True,
            category=SettingCategory.GENERATION,
            description="Whether the model should stream partial output."),
]


########################################################################
#                              CLASSES                                 #
########################################################################
class BaseModel(ABC):
  """Abstract base class for all model implementations."""

  # RUNTIME ``ParamSpec`` declarations for this model. Subclasses may
  # replace or extend this list to advertise their generation knobs.
  runtime_params: List[ParamSpec] = COMMON_TEXT_RUNTIME_PARAMS

  def __init__(self, model_name: str):
    self.model_name = model_name

  @abstractmethod
  def generate(self, conversation: Conversation, **kwargs) -> Generator[str, None, str]:
    """Generate a response based on the given conversation.

    Yields individual tokens/chunks as they become available. Returns
    the full response string when the generator is exhausted. The model
    must NOT modify the ``Conversation``; that is the deployment
    layer's responsibility.
    """
    pass

  def update_settings(self, model_settings: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """
    Build a settings dict for a generation call.

    Starts from this model's ``runtime_params`` defaults, layers in any
    caller-provided ``model_settings`` (typically hard-coded per-call
    overrides from the concrete model's ``generate`` method), then
    applies ``kwargs`` for every name present in the declared specs.

    Undeclared kwargs are ignored — the filtering keeps the settings
    dict anchored to the model's published contract.
    """
    settings: Dict[str, Any] = {p.name: p.default for p in self.runtime_params}

    if model_settings:
      for key, value in model_settings.items():
        settings[key] = value

    declared_names = {p.name for p in self.runtime_params}
    for key, value in kwargs.items():
      if key in declared_names:
        settings[key] = value

    return settings
