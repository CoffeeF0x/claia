"""
Local architecture base class.

Base for architectures whose instance holds in-process model weights.
Served by the ``transformers`` deployment, which owns instantiation
(and therefore when loading happens) and teardown.
"""

from abc import abstractmethod
from typing import List

# Internal dependencies
from .base import BaseArchitecture


########################################################################
#                               CLASSES                                #
########################################################################
class LocalArchitecture(BaseArchitecture):
  """Base class for in-process, weight-holding architecture implementations."""

  deployment = "transformers"

  model = None

  def __init__(self, model_name: str, model_path: str, defer_loading: bool = False, device: str = "cpu"):
    super().__init__(model_name)
    self.model_path = model_path
    self.loaded = not defer_loading
    self.device = device

    if not defer_loading:
      self.load()

  def is_loaded(self) -> bool:
    """Check if the model is currently loaded."""
    return self.loaded

  @abstractmethod
  def load(self) -> None:
    """Load the model."""
    pass

  @abstractmethod
  def unload(self) -> None:
    """Unload the model."""
    self.model = None

  @abstractmethod
  def tokenize(self, text: str) -> List[int]:
    """Tokenize the input text."""
    pass

  @abstractmethod
  def detokenize(self, tokens: List[int]) -> str:
    """Convert tokens back to text."""
    pass

  @abstractmethod
  def download(self, model_path: str) -> None:
    """Download the model to the specified path."""
    pass
