"""
Dummy model architecture plugin.

Provides the architecture implementation for the dummy streaming model.
"""

import logging
from typing import Type

from .base import BaseArchitecture
from ..decorators import architecture
from ..models.dummy import DummyModel


logger = logging.getLogger(__name__)


@architecture
@architecture.name("dummy")
@architecture.title("Dummy Architecture")
@architecture.description("Dummy local model architecture for testing")
class DummyArchitecturePlugin(BaseArchitecture):
  """Dummy architecture plugin for testing purposes."""

  def get_model_class(self) -> Type:
    logger.debug("Providing DummyModel class for dummy architecture")
    return DummyModel
