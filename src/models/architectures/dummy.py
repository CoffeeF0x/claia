"""
Dummy model architecture plugin.

Provides the architecture implementation for the dummy streaming model.
"""

import logging
from typing import Optional, Type

# Internal dependencies
from .lib.dummy import DummyModel


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                               CLASSES                                #
########################################################################
class DummyArchitecturePlugin:
  """Dummy architecture plugin for testing purposes."""

  def get_model_class(self, model_name: str) -> Optional[Type]:
    """
    Get the model class for dummy models.

    Args:
        model_name: Canonical model name

    Returns:
        DummyModel class for testing
    """
    logger.debug(f"Providing DummyModel class for testing model {model_name}")
    return DummyModel
