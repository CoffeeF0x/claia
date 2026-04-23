"""
Dummy model architecture plugin.

Provides the architecture implementation for the dummy streaming model.
"""

import logging
from typing import Type

from .base import BaseArchitecture
from ..models.dummy import DummyModel
from ..plugins.base import ArchitectureInfo


logger = logging.getLogger(__name__)


class DummyArchitecturePlugin(BaseArchitecture):
  """Dummy architecture plugin for testing purposes."""

  info = ArchitectureInfo(
    name="dummy",
    title="Dummy Architecture",
    description="Dummy local model architecture for testing",
  )

  def get_model_class(self) -> Type:
    logger.debug("Providing DummyModel class for dummy architecture")
    return DummyModel
