"""
Dummy model architecture plugin.

Provides the architecture implementation for the dummy streaming model.
"""

import logging
import pluggy
from typing import Optional, Type

# Internal dependencies
from .lib.dummy import DummyModel


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)

# Create hookimpl decorator for this plugin namespace
hookimpl = pluggy.HookimplMarker("claia_architectures")


########################################################################
#                               CLASSES                                #
########################################################################
class DummyArchitecturePlugin:
  """Dummy architecture plugin for testing purposes."""

  @hookimpl
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
